#!/usr/bin/env python3
"""Build static-only evidence for global UE4/ARK candidate addresses."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_core_dump_evidence_pack as core_pack  # noqa: E402


SCHEMA = "obelisk.static-global-promotion-evidence.v1"
STATIC_ARTIFACT_PROVENANCE_SCHEMA = "obelisk.static-artifact-provenance.v1"
FUOBJECTARRAY_FIELD_WINDOW_SCHEMA = "obelisk.fuobjectarray-field-window-redacted.v1"
PROVENANCE_PRODUCER = Path(__file__).name
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
SUPPORTED_CANDIDATE_KINDS = {"gobjects", "fname_root"}
EXPECTED_ARTIFACT_TOOLS = {
    "readelf_programs": "readelf",
    "readelf_sections": "readelf",
    "objdump": "objdump",
}
PATH_KEYS = {
    "artifact",
    "binary",
    "copied_to",
    "path",
    "source",
    "stderr",
    "stdout",
}
SEMANTIC_ROLE_KEYWORDS = (
    ("destructor", ("destructor", "destroy", "dtor", "shutdown", "teardown", "cleanup", "release", "free")),
    ("reset", ("reset", "clear", "zero", "empty")),
    ("bootstrap", ("bootstrap", "startup", "staticinit", "staticconstructor", "staticconstruct")),
    ("init", ("init", "initialize", "construct", "constructor", "ctor", "setup", "alloc", "create")),
    ("lookup", ("lookup", "find", "resolve", "search", "contains", "index", "get")),
)
GOBJECTS_FIELD_NAMES = {"root", "chunks", "count", "serial"}
FIELD_WINDOW_BLOCKER = "missing_gobjects_coherent_field_window"


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_approved_offline_workspace_path(path: Path) -> bool:
    resolved = path.resolve()
    return any(is_relative_to(resolved, root.resolve()) for root in APPROVED_OFFLINE_WORKSPACE_ROOTS)


def reject_protected_path(path: Path, label: str) -> None:
    expanded = path.expanduser()
    if expanded.is_absolute() and (
        expanded == PROTECTED_SERVER_ROOT or is_relative_to(expanded, PROTECTED_SERVER_ROOT)
    ) and not is_approved_offline_workspace_path(expanded):
        raise SystemExit(f"{label} must not be under {PROTECTED_SERVER_ROOT}")
    protected = PROTECTED_SERVER_ROOT.resolve()
    resolved = expanded.resolve()
    if (resolved == protected or is_relative_to(resolved, protected)) and not is_approved_offline_workspace_path(resolved):
        raise SystemExit(f"{label} must not be under {PROTECTED_SERVER_ROOT}")


def protected_path_detail(path: Path, *, base_dir: Path | None = None) -> str | None:
    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() or base_dir is None else base_dir / expanded
    if candidate.is_absolute() and (
        candidate == PROTECTED_SERVER_ROOT or is_relative_to(candidate, PROTECTED_SERVER_ROOT)
    ) and not is_approved_offline_workspace_path(candidate):
        return str(candidate)
    resolved = candidate.resolve()
    protected = PROTECTED_SERVER_ROOT.resolve()
    if (resolved == protected or is_relative_to(resolved, protected)) and not is_approved_offline_workspace_path(resolved):
        return str(resolved)
    return None


def key_names_path(value: str) -> bool:
    normalized = value.casefold()
    return normalized in PATH_KEYS or normalized.endswith("_path") or normalized.endswith("_file")


def find_protected_path_in_provenance(value: object, *, base_dir: Path, trail: str = "source_provenance") -> dict[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, str) and key_names_path(str(key)):
                detail = protected_path_detail(Path(child), base_dir=base_dir)
                if detail is not None:
                    return {"field": child_trail, "path": detail}
            elif isinstance(child, (dict, list)):
                found = find_protected_path_in_provenance(child, base_dir=base_dir, trail=child_trail)
                if found is not None:
                    return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_protected_path_in_provenance(child, base_dir=base_dir, trail=f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str):
        detail = protected_path_detail(Path(value), base_dir=base_dir)
        if detail is not None:
            return {"field": trail, "path": detail}
    return None


def expected_producer(payload: dict[str, object], artifact_kind: str) -> bool:
    producer = payload.get("producer")
    if producer == PROVENANCE_PRODUCER:
        return True
    expected_tool = EXPECTED_ARTIFACT_TOOLS[artifact_kind]
    tool = payload.get("tool")
    if tool == expected_tool:
        return True
    command = payload.get("command")
    if isinstance(command, list) and command:
        first = command[0]
        if isinstance(first, str) and Path(first).name == expected_tool:
            return True
    return False


def invalid_provenance(
    provenance_path: Path,
    reason: str,
    **details: object,
) -> dict[str, object]:
    return {
        "path": str(provenance_path),
        "verified": False,
        "reason": reason,
        **details,
    }


def validate_static_artifact_provenance(
    *,
    provenance_path: Path,
    source_sha256: str,
    binary_sha256: str,
    artifact_kind: str,
) -> dict[str, object]:
    try:
        provenance_payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return invalid_provenance(provenance_path, "malformed_static_artifact_provenance")
    if not isinstance(provenance_payload, dict):
        return invalid_provenance(
            provenance_path,
            "static_artifact_provenance_not_object",
            recorded_type=type(provenance_payload).__name__,
        )

    source_provenance = provenance_payload.get("source_provenance")
    if source_provenance is not None:
        protected = find_protected_path_in_provenance(source_provenance, base_dir=provenance_path.parent)
        if protected is not None:
            return invalid_provenance(
                provenance_path,
                "protected_static_artifact_source_provenance_path",
                source_provenance_field=protected["field"],
                protected_path=protected["path"],
            )

    if provenance_payload.get("schema") != STATIC_ARTIFACT_PROVENANCE_SCHEMA:
        return invalid_provenance(
            provenance_path,
            "static_artifact_provenance_schema_mismatch",
            expected_schema=STATIC_ARTIFACT_PROVENANCE_SCHEMA,
            recorded_schema=provenance_payload.get("schema"),
        )
    if provenance_payload.get("artifact_kind") != artifact_kind:
        return invalid_provenance(
            provenance_path,
            "static_artifact_provenance_kind_mismatch",
            expected_artifact_kind=artifact_kind,
            recorded_artifact_kind=provenance_payload.get("artifact_kind"),
        )
    if not expected_producer(provenance_payload, artifact_kind):
        return invalid_provenance(
            provenance_path,
            "static_artifact_provenance_producer_mismatch",
            expected_producer=PROVENANCE_PRODUCER,
            expected_tool=EXPECTED_ARTIFACT_TOOLS[artifact_kind],
            recorded_producer=provenance_payload.get("producer"),
            recorded_tool=provenance_payload.get("tool"),
        )

    recorded_binary_sha = provenance_payload.get("binary_sha256")
    recorded_artifact_sha = provenance_payload.get("artifact_sha256")
    if provenance_payload.get("verified") is not True:
        return invalid_provenance(provenance_path, "static_artifact_provenance_not_verified")
    if recorded_binary_sha != binary_sha256:
        return invalid_provenance(
            provenance_path,
            "static_artifact_binary_sha256_mismatch",
            expected_binary_sha256=binary_sha256,
            recorded_binary_sha256=recorded_binary_sha,
        )
    if recorded_artifact_sha != source_sha256:
        return invalid_provenance(
            provenance_path,
            "static_artifact_sha256_mismatch",
            expected_artifact_sha256=source_sha256,
            recorded_artifact_sha256=recorded_artifact_sha,
        )
    return {
        "path": str(provenance_path),
        "verified": True,
        "schema": provenance_payload.get("schema"),
        "artifact_kind": provenance_payload.get("artifact_kind"),
        "producer": provenance_payload.get("producer"),
        "binary_sha256": recorded_binary_sha,
        "artifact_sha256": recorded_artifact_sha,
        "command": provenance_payload.get("command"),
        "tool": provenance_payload.get("tool"),
        "source_provenance": source_provenance,
    }


def parse_candidate_kind(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("candidate kind must be LABEL=KIND")
    label, kind = value.split("=", 1)
    label = label.strip()
    kind = kind.strip()
    if not label:
        raise argparse.ArgumentTypeError("candidate kind label must not be empty")
    if kind not in SUPPORTED_CANDIDATE_KINDS:
        supported = ", ".join(sorted(SUPPORTED_CANDIDATE_KINDS))
        raise argparse.ArgumentTypeError(f"unsupported candidate kind {kind}; expected one of: {supported}")
    return label, kind


def validate_candidates(values: list[str], kind_overrides: dict[str, str]) -> list[tuple[str, int]]:
    candidates = [core_pack.parse_candidate(value) for value in values]
    labels: set[str] = set()
    addresses: set[int] = set()
    for label, address in candidates:
        if label in labels:
            raise SystemExit(f"duplicate candidate label: {label}")
        if address in addresses:
            raise SystemExit(f"duplicate candidate address: {core_pack.normalize_hex(address)}")
        labels.add(label)
        addresses.add(address)
    for label, _address in candidates:
        candidate_kind(label, kind_overrides)
    unknown_overrides = sorted(set(kind_overrides) - labels)
    if unknown_overrides:
        raise SystemExit(f"candidate kind supplied for unknown label: {','.join(unknown_overrides)}")
    return candidates


def copy_or_generate_artifact(
    *,
    source: Path | None,
    command: list[str],
    output_path: Path,
    binary_sha256: str,
    artifact_kind: str,
) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source is not None:
        output_path.write_text(source.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        source_sha256 = core_pack.sha256_file(source)
        provenance_path = Path(f"{source}.provenance.json")
        provenance: dict[str, object] = {
            "path": str(provenance_path),
            "verified": False,
            "reason": "missing_static_artifact_provenance",
        }
        if provenance_path.exists() or provenance_path.is_symlink():
            reject_protected_path(provenance_path, "static artifact provenance")
            provenance = validate_static_artifact_provenance(
                provenance_path=provenance_path,
                source_sha256=source_sha256,
                binary_sha256=binary_sha256,
                artifact_kind=artifact_kind,
            )
        copied_sha256 = core_pack.sha256_file(output_path)
        output_provenance = {
            "schema": STATIC_ARTIFACT_PROVENANCE_SCHEMA,
            "verified": bool(provenance.get("verified")),
            "artifact_kind": artifact_kind,
            "producer": PROVENANCE_PRODUCER,
            "binary_sha256": binary_sha256,
            "artifact_sha256": copied_sha256,
            "source_artifact_sha256": source_sha256,
            "source_provenance": provenance,
            "command": provenance.get("command") if provenance.get("verified") else None,
            "tool": provenance.get("tool") if provenance.get("verified") else None,
        }
        output_provenance_path = Path(f"{output_path}.provenance.json")
        output_provenance_path.write_text(json.dumps(output_provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "source": str(source),
            "source_sha256": source_sha256,
            "copied_to": str(output_path),
            "copied_sha256": copied_sha256,
            "command": None,
            "returncode": 0,
            "provenance": provenance,
            "output_provenance": str(output_provenance_path),
        }
    record = core_pack.run_command(command, output_path)
    artifact_sha256 = core_pack.sha256_file(output_path)
    record["stdout_sha256"] = artifact_sha256
    record["provenance"] = {
        "verified": True,
        "reason": "generated_from_binary",
        "binary_sha256": binary_sha256,
    }
    output_provenance = {
        "schema": STATIC_ARTIFACT_PROVENANCE_SCHEMA,
        "verified": True,
        "artifact_kind": artifact_kind,
        "producer": PROVENANCE_PRODUCER,
        "binary_sha256": binary_sha256,
        "artifact_sha256": artifact_sha256,
        "command": command,
        "tool": command[0] if command else None,
    }
    output_provenance_path = Path(f"{output_path}.provenance.json")
    output_provenance_path.write_text(json.dumps(output_provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    record["output_provenance"] = str(output_provenance_path)
    return record


def parse_readelf_segments(path: Path) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts or parts[0] != "LOAD" or len(parts) < 6:
            continue
        try:
            start = int(parts[2], 16)
            mem_size = int(parts[5], 16)
        except ValueError:
            continue
        flags = "".join(part for part in parts[6:] if not part.startswith("0x"))
        segments.append(
            {
                "type": "LOAD",
                "virtual_address": core_pack.normalize_hex(start),
                "mem_size": mem_size,
                "end_address": core_pack.normalize_hex(start + mem_size),
                "flags": flags,
            }
        )
    return segments


def parse_readelf_sections(path: Path) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("["):
            continue
        parts = stripped.replace("[", " [ ").replace("]", " ] ").split()
        if "]" not in parts:
            continue
        close_index = parts.index("]")
        if len(parts) <= close_index + 5:
            continue
        name = parts[close_index + 1]
        try:
            address = int(parts[close_index + 3], 16)
            size = int(parts[close_index + 5], 16)
        except ValueError:
            continue
        if not name or size <= 0:
            continue
        sections.append(
            {
                "name": name,
                "address": core_pack.normalize_hex(address),
                "size": size,
                "end_address": core_pack.normalize_hex(address + size),
                "flags": parts[close_index + 7] if len(parts) > close_index + 7 else "",
            }
        )
    return sections


def containing_range(address: int, ranges: list[dict[str, object]], label_key: str) -> dict[str, object] | None:
    for item in ranges:
        start = int(str(item["address" if label_key == "section" else "virtual_address"]), 16)
        end = int(str(item["end_address"]), 16)
        if start <= address < end:
            return item
    return None


def candidate_kind(label: str, kind_overrides: dict[str, str]) -> str:
    if label in kind_overrides:
        return kind_overrides[label]
    normalized = label.casefold()
    compact = "".join(character for character in normalized if character.isalnum())
    if "gobject" in normalized or "guobject" in normalized:
        return "gobjects"
    if "gobject" in compact or "guobject" in compact:
        return "gobjects"
    if "gname" in normalized or "fname" in normalized:
        return "fname_root"
    if "gname" in compact or "fname" in compact:
        return "fname_root"
    raise SystemExit(
        "unsupported candidate kind for label "
        f"{label}; use a GObjects/FName label or --candidate-kind {label}=gobjects|fname_root"
    )


def static_xref_targets(candidates: list[tuple[str, int]], kind_overrides: dict[str, str]) -> dict[str, str]:
    targets: dict[str, str] = {}
    for label, address in candidates:
        kind = candidate_kind(label, kind_overrides)
        if kind == "gobjects":
            targets.update(core_pack.gobjects_static_xref_targets([(label, address)]))
        elif kind == "fname_root":
            targets.update(core_pack.fname_static_xref_targets([(label, address)]))
    return targets


def enrich_xrefs_with_ranges(
    payload: dict[str, object],
    *,
    segments: list[dict[str, object]],
    sections: list[dict[str, object]],
) -> dict[str, object]:
    raw_xrefs = payload.get("xrefs")
    if not isinstance(raw_xrefs, dict):
        return payload
    for refs in raw_xrefs.values():
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            try:
                instruction_address = int(str(ref.get("instruction_address", "0")), 16)
            except ValueError:
                ref["instruction_segment"] = None
                ref["instruction_section"] = None
                ref["semantic"] = classify_xref_semantics(ref)
                continue
            ref["instruction_segment"] = containing_range(instruction_address, segments, "segment")
            ref["instruction_section"] = containing_range(instruction_address, sections, "section")
            ref["semantic"] = classify_xref_semantics(ref)
    return payload


def candidate_xrefs(
    *,
    label: str,
    address_hex: str,
    xrefs_payload: dict[str, object],
) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    raw_xrefs = xrefs_payload.get("xrefs", {})
    if not isinstance(raw_xrefs, dict):
        return refs
    for target_address, target_refs in raw_xrefs.items():
        if not isinstance(target_refs, list):
            continue
        for ref in target_refs:
            if not isinstance(ref, dict):
                continue
            target_label = str(ref.get("target_label", ""))
            if target_address == address_hex or target_label.startswith(f"{label}."):
                refs.append(ref)
    return refs


def semantic_role_from_function_label(function_label: object) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(function_label, str) or not function_label:
        return "unknown", []
    split_label = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", function_label)
    normalized = split_label.casefold()
    token_list = re.findall(r"[a-z0-9]+", normalized)
    tokens = set(token_list)
    compact = "".join(token_list)
    for role, keywords in SEMANTIC_ROLE_KEYWORDS:
        for keyword in keywords:
            if keyword in tokens or (len(keyword) > 3 and keyword in compact):
                return role, [{"source": "function_label", "value": function_label, "matched": keyword}]
    return "unknown", []


def semantic_role_from_instruction(instruction: object) -> tuple[str, list[dict[str, str]]]:
    if not isinstance(instruction, str) or not instruction:
        return "unknown", []
    normalized = instruction.casefold()
    if re.search(r"\bmov[a-z]*\s+[^,]*ptr\s+\[rip[^\]]+\],\s*(?:0x0|\$?0)\b", normalized):
        return "reset", [{"source": "instruction", "matched": "rip_relative_zero_store"}]
    return "unknown", []


def xref_semantic_context(target_label: object) -> dict[str, str]:
    if not isinstance(target_label, str) or not target_label:
        return {"context": "unknown"}
    owner, separator, field = target_label.rpartition(".")
    if separator and field in GOBJECTS_FIELD_NAMES:
        return {"context": "gobjects_field", "field": field, "target": target_label}
    if separator and field == "root_slot":
        return {"context": "fname_root_slot", "field": field, "target": target_label}
    return {"context": "global_xref", "target": target_label}


def classify_xref_semantics(ref: dict[str, object]) -> dict[str, object]:
    role, evidence = semantic_role_from_function_label(ref.get("function_label"))
    if role == "unknown":
        role, evidence = semantic_role_from_instruction(ref.get("instruction"))
    return {
        "role": role,
        **xref_semantic_context(ref.get("target_label")),
        "evidence": evidence,
    }


def semantic_for_ref(ref: dict[str, object]) -> dict[str, object]:
    semantic = ref.get("semantic")
    if isinstance(semantic, dict):
        return semantic
    return classify_xref_semantics(ref)


def summarize_xref_semantics(refs: list[dict[str, object]]) -> dict[str, object]:
    role_counts: dict[str, int] = {}
    contexts: set[str] = set()
    fields: set[str] = set()
    for ref in refs:
        semantic = semantic_for_ref(ref)
        role = str(semantic.get("role", "unknown"))
        if role != "unknown":
            role_counts[role] = role_counts.get(role, 0) + 1
        context = semantic.get("context")
        if isinstance(context, str) and context != "unknown":
            contexts.add(context)
        field = semantic.get("field")
        if isinstance(field, str):
            fields.add(field)
    return {
        "role_counts": dict(sorted(role_counts.items())),
        "contexts": sorted(contexts),
        "fields": sorted(fields),
    }


def is_code_backed_xref(ref: dict[str, object]) -> bool:
    segment = ref.get("instruction_segment")
    section = ref.get("instruction_section")
    if not isinstance(segment, dict) or not isinstance(section, dict):
        return False
    return "E" in str(segment.get("flags", "")) and "X" in str(section.get("flags", ""))


def gobjects_code_backed_windows(
    refs: list[dict[str, object]],
    required_labels: set[str],
) -> list[dict[str, object]]:
    code_refs = sorted(
        (
            ref
            for ref in refs
            if bool(ref.get("target_is_rip_relative")) and is_code_backed_xref(ref)
        ),
        key=lambda ref: int(str(ref.get("instruction_address", "0")), 16),
    )
    current: dict[str, object] | None = None
    current_labels: set[str] = set()
    last_address: int | None = None
    current_function_identity: tuple[str | None, str | None] | None = None
    windows: list[dict[str, object]] = []

    def finalize_group() -> None:
        if current is None:
            return
        missing_labels = sorted(required_labels - current_labels)
        present_labels = sorted(required_labels & current_labels)
        reject_reasons = []
        if missing_labels:
            reject_reasons.append("missing_required_labels")
        if bool(current["oversized"]):
            reject_reasons.append("oversized_anchor_window")
        current["present_required_labels"] = present_labels
        current["missing_required_labels"] = missing_labels
        current["reject_reasons"] = reject_reasons
        windows.append(current)

    for ref in code_refs:
        try:
            address = int(str(ref.get("instruction_address", "0")), 16)
        except ValueError:
            continue
        function_identity = (
            str(ref.get("function_start")) if ref.get("function_start") is not None else None,
            str(ref.get("function_label")) if ref.get("function_label") is not None else None,
        )
        crosses_known_function = (
            current_function_identity is not None
            and function_identity != current_function_identity
            and any(current_function_identity)
            and any(function_identity)
        )
        if (
            current is None
            or last_address is None
            or address - last_address > core_pack.ANCHOR_GROUP_MAX_GAP_BYTES
            or crosses_known_function
        ):
            finalize_group()
            current = {
                "anchor_start": ref.get("instruction_address"),
                "anchor_end": ref.get("instruction_address"),
                "function_start": ref.get("function_start"),
                "function_label": ref.get("function_label"),
                "role": "unknown",
                "role_counts": {},
                "context": "gobjects_required_field_window",
                "contexts": [],
                "fields": [],
                "semantic_evidence": [],
                "xref_count": 0,
                "target_labels": [],
                "sample_instruction_addresses": [],
                "anchor_span_bytes": 0,
                "oversized": False,
                "interpretation": "concrete-instruction-window",
            }
            current_labels = set()
            current_function_identity = function_identity
        current["anchor_end"] = ref.get("instruction_address")
        current["xref_count"] = int(current["xref_count"]) + 1
        start_address = int(str(current["anchor_start"]), 16)
        current["anchor_span_bytes"] = address - start_address
        current["oversized"] = (
            int(current["xref_count"]) >= core_pack.ANCHOR_GROUP_OVERSIZED_XREFS
            or int(current["anchor_span_bytes"]) >= core_pack.ANCHOR_GROUP_OVERSIZED_SPAN_BYTES
        )
        current["interpretation"] = (
            "contaminated-anchor-window" if bool(current["oversized"]) else "concrete-instruction-window"
        )
        target_label = str(ref.get("target_label", ""))
        current_labels.add(target_label)
        target_labels = current["target_labels"]
        if isinstance(target_labels, list) and target_label not in target_labels:
            target_labels.append(target_label)
        semantic = semantic_for_ref(ref)
        role = str(semantic.get("role", "unknown"))
        if role != "unknown":
            role_counts = current["role_counts"]
            if isinstance(role_counts, dict):
                role_counts[role] = int(role_counts.get(role, 0)) + 1
                current["role"] = next(iter(role_counts)) if len(role_counts) == 1 else "mixed"
        context = semantic.get("context")
        contexts = current["contexts"]
        if isinstance(context, str) and context != "unknown" and isinstance(contexts, list) and context not in contexts:
            contexts.append(context)
        field = semantic.get("field")
        fields = current["fields"]
        if isinstance(field, str) and isinstance(fields, list) and field not in fields:
            fields.append(field)
        evidence = semantic.get("evidence")
        semantic_evidence = current["semantic_evidence"]
        if isinstance(evidence, list) and isinstance(semantic_evidence, list):
            for item in evidence:
                if isinstance(item, dict) and item not in semantic_evidence and len(semantic_evidence) < 5:
                    semantic_evidence.append(item)
        samples = current["sample_instruction_addresses"]
        if isinstance(samples, list) and len(samples) < 5:
            samples.append(ref.get("instruction_address"))
        last_address = address
    finalize_group()
    return windows


def coherent_code_backed_window(
    refs: list[dict[str, object]],
    required_labels: set[str],
) -> dict[str, object] | None:
    for window in gobjects_code_backed_windows(refs, required_labels):
        if not window["missing_required_labels"] and not bool(window["oversized"]):
            return window
    return None


def gobjects_coherent_window_near_miss(
    refs: list[dict[str, object]],
    required_labels: set[str],
) -> dict[str, object]:
    def missing_required_label_count(window: dict[str, object]) -> int:
        missing = window["missing_required_labels"]
        return len(missing) if isinstance(missing, list) else 99

    windows = [
        window
        for window in gobjects_code_backed_windows(refs, required_labels)
        if window["missing_required_labels"] or bool(window["oversized"])
    ]
    if windows:
        closest_missing_count = min(missing_required_label_count(window) for window in windows)
        windows = [window for window in windows if missing_required_label_count(window) == closest_missing_count]
    windows.sort(
        key=lambda window: (
            missing_required_label_count(window),
            bool(window["oversized"]),
            -int(window["xref_count"]),
            str(window["anchor_start"]),
        )
    )
    return {
        "context": "gobjects_required_field_window",
        "required_labels": sorted(required_labels),
        "eligible_xref_count": sum(int(window["xref_count"]) for window in windows),
        "windows": windows[:8],
    }


def gobjects_split_field_window_evidence(
    refs: list[dict[str, object]],
    required_labels: set[str],
) -> dict[str, object]:
    labels_by_field = {
        label.rpartition(".")[2]: label
        for label in required_labels
        if label.rpartition(".")[2] in GOBJECTS_FIELD_NAMES
    }
    root_chunks_count = {
        labels_by_field["root"],
        labels_by_field["chunks"],
        labels_by_field["count"],
    }
    chunks_count_serial = {
        labels_by_field["chunks"],
        labels_by_field["count"],
        labels_by_field["serial"],
    }
    serial_label = labels_by_field["serial"]
    root_label = labels_by_field["root"]
    windows = gobjects_code_backed_windows(refs, required_labels)

    def split_windows(present_labels: set[str], missing_labels: set[str]) -> list[dict[str, object]]:
        matches = []
        for window in windows:
            window_present = set(str(label) for label in window.get("present_required_labels", []))
            window_missing = set(str(label) for label in window.get("missing_required_labels", []))
            if (
                present_labels <= window_present
                and window_missing == missing_labels
                and not bool(window.get("oversized"))
            ):
                matches.append(window)
        matches.sort(
            key=lambda window: (
                -int(window["xref_count"]),
                int(window["anchor_span_bytes"]),
                str(window["anchor_start"]),
            )
        )
        return matches[:8]

    root_chunks_count_windows = split_windows(root_chunks_count, {serial_label})
    chunks_count_serial_windows = split_windows(chunks_count_serial, {root_label})
    status = (
        "split_near_miss"
        if root_chunks_count_windows and chunks_count_serial_windows
        else "split_incomplete"
    )
    return {
        "context": "gobjects_split_required_field_windows",
        "status": status,
        "required_labels": sorted(required_labels),
        "coherent_contract_satisfied": False,
        "does_not_satisfy": "missing_gobjects_coherent_field_window",
        "interpretation": (
            "Separate non-oversized windows can support partial field clusters, "
            "but split windows are not a coherent root/chunks/count/serial contract."
        ),
        "root_chunks_count": {
            "required_present_labels": sorted(root_chunks_count),
            "required_missing_labels": [serial_label],
            "window_count": len(root_chunks_count_windows),
            "windows": root_chunks_count_windows,
        },
        "chunks_count_serial": {
            "required_present_labels": sorted(chunks_count_serial),
            "required_missing_labels": [root_label],
            "window_count": len(chunks_count_serial_windows),
            "windows": chunks_count_serial_windows,
        },
    }


def has_mixed_function_window(refs: list[dict[str, object]], required_labels: set[str]) -> bool:
    code_refs = sorted(
        (
            ref
            for ref in refs
            if bool(ref.get("target_is_rip_relative")) and is_code_backed_xref(ref)
        ),
        key=lambda ref: int(str(ref.get("instruction_address", "0")), 16),
    )
    current_labels: set[str] = set()
    current_functions: set[tuple[str, str]] = set()
    first_address: int | None = None
    last_address: int | None = None

    def current_is_mixed_required_window() -> bool:
        known_functions = {identity for identity in current_functions if any(identity)}
        return required_labels <= current_labels and len(known_functions) > 1

    for ref in code_refs:
        try:
            address = int(str(ref.get("instruction_address", "0")), 16)
        except ValueError:
            continue
        if first_address is None or last_address is None or address - last_address > core_pack.ANCHOR_GROUP_MAX_GAP_BYTES:
            if current_is_mixed_required_window():
                return True
            first_address = address
            current_labels = set()
            current_functions = set()
        target_label = str(ref.get("target_label", ""))
        current_labels.add(target_label)
        current_functions.add((str(ref.get("function_start") or ""), str(ref.get("function_label") or "")))
        last_address = address
    return current_is_mixed_required_window()


def candidate_payload(
    *,
    label: str,
    address: int,
    kind_overrides: dict[str, str],
    segments: list[dict[str, object]],
    sections: list[dict[str, object]],
    xrefs_payload: dict[str, object],
    field_window_evidence: dict[str, dict[str, object]],
) -> dict[str, object]:
    address_hex = core_pack.normalize_hex(address)
    kind = candidate_kind(label, kind_overrides)
    xrefs = candidate_xrefs(label=label, address_hex=address_hex, xrefs_payload=xrefs_payload)
    access_counts: dict[str, int] = {}
    target_xref_counts: dict[str, int] = {}
    target_code_backed_xref_counts: dict[str, int] = {}
    rip_relative_xrefs = 0
    immediate_xrefs = 0
    for ref in xrefs:
        if not isinstance(ref, dict):
            continue
        access = str(ref.get("access", "unknown"))
        access_counts[access] = access_counts.get(access, 0) + 1
        target_label = str(ref.get("target_label", "unknown"))
        target_xref_counts[target_label] = target_xref_counts.get(target_label, 0) + 1
        instruction = str(ref.get("instruction", "")).lower()
        if bool(ref.get("target_is_rip_relative")):
            rip_relative_xrefs += 1
            if is_code_backed_xref(ref):
                target_code_backed_xref_counts[target_label] = target_code_backed_xref_counts.get(target_label, 0) + 1
        elif address_hex[2:] in instruction or address_hex in instruction:
            immediate_xrefs += 1

    blockers = []
    if containing_range(address, segments, "segment") is None:
        blockers.append("candidate_not_in_load_segment")
    if containing_range(address, sections, "section") is None:
        blockers.append("candidate_not_in_section")
    if rip_relative_xrefs <= 0:
        blockers.append("missing_rip_relative_xref")
    if kind == "gobjects":
        required_labels = {f"{label}.root", f"{label}.chunks", f"{label}.count", f"{label}.serial"}
        missing = sorted(required_labels - set(target_code_backed_xref_counts))
        if missing:
            blockers.append(f"missing_gobjects_code_backed_field_xrefs:{','.join(missing)}")
        coherent_window = coherent_code_backed_window(xrefs, required_labels)
        near_miss = gobjects_coherent_window_near_miss(xrefs, required_labels) if coherent_window is None else None
        split_evidence = (
            gobjects_split_field_window_evidence(xrefs, required_labels) if coherent_window is None else None
        )
        if not missing and coherent_window is None:
            if has_mixed_function_window(xrefs, required_labels):
                blockers.append("mixed_function_window")
            else:
                blockers.append(FIELD_WINDOW_BLOCKER)
        redacted_field_window = field_window_evidence.get(label)
        if redacted_field_window is not None and FIELD_WINDOW_BLOCKER in blockers:
            blockers = [blocker for blocker in blockers if blocker != FIELD_WINDOW_BLOCKER]
        elif redacted_field_window is None:
            redacted_field_window = None
    else:
        coherent_window = None
        near_miss = None
        split_evidence = None
        redacted_field_window = None
    if kind == "fname_root" and not any(target.endswith(".root_slot") for target in target_code_backed_xref_counts):
        blockers.append("missing_fname_root_slot_xref")

    return {
        "label": label,
        "kind": kind,
        "address": address_hex,
        "segment": containing_range(address, segments, "segment"),
        "section": containing_range(address, sections, "section"),
        "xref_count": len(xrefs),
        "rip_relative_xref_count": rip_relative_xrefs,
        "immediate_xref_count": immediate_xrefs,
        "access_counts": dict(sorted(access_counts.items())),
        "target_xref_counts": dict(sorted(target_xref_counts.items())),
        "target_code_backed_xref_counts": dict(sorted(target_code_backed_xref_counts.items())),
        "semantic_summary": summarize_xref_semantics(xrefs),
        "static_contract": {
            "satisfied": not blockers,
            "blockers": blockers,
            "coherent_window": coherent_window,
            "near_miss": near_miss,
            "split_evidence": split_evidence,
            "redacted_field_window_evidence": redacted_field_window,
        },
    }


def load_fuobjectarray_field_window_evidence(path: Path, binary_sha256: str) -> tuple[str, dict[str, object]]:
    reject_protected_path(path, "--fuobjectarray-field-window-evidence")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: field-window evidence must be a JSON object")
    if payload.get("schema") != FUOBJECTARRAY_FIELD_WINDOW_SCHEMA:
        raise SystemExit(f"{path}: unsupported field-window evidence schema")
    if payload.get("status") != "accepted_internal_static_evidence":
        raise SystemExit(f"{path}: field-window evidence status is not accepted")
    binary = payload.get("binary")
    if not isinstance(binary, dict) or binary.get("sha256") != binary_sha256:
        raise SystemExit(f"{path}: field-window evidence binary SHA256 mismatch")
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("kind") != "gobjects":
        raise SystemExit(f"{path}: field-window evidence candidate kind must be gobjects")
    label = candidate.get("label")
    if not isinstance(label, str) or not label:
        raise SystemExit(f"{path}: field-window evidence candidate label is missing")
    window = payload.get("fuobjectarray_window")
    if not isinstance(window, dict):
        raise SystemExit(f"{path}: field-window evidence missing fuobjectarray_window")
    same_base_flow = window.get("same_base_flow")
    if not isinstance(same_base_flow, dict) or same_base_flow.get("proven") is not True:
        raise SystemExit(f"{path}: field-window evidence does not prove same-base flow")
    fields = window.get("required_fields")
    if not isinstance(fields, dict):
        raise SystemExit(f"{path}: field-window evidence missing required_fields")
    for field_name in ("root", "chunks", "count", "serial"):
        field = fields.get(field_name)
        if not isinstance(field, dict) or field.get("present") is not True:
            raise SystemExit(f"{path}: field-window evidence missing field {field_name}")
    contract = payload.get("builder_contract")
    if not isinstance(contract, dict):
        raise SystemExit(f"{path}: field-window evidence missing builder_contract")
    if contract.get("candidate_static_contract_blocker_to_clear") != FIELD_WINDOW_BLOCKER:
        raise SystemExit(f"{path}: field-window evidence clears the wrong blocker")
    if contract.get("promotion_gate_ready") is not False:
        raise SystemExit(f"{path}: field-window evidence must keep promotion_gate_ready=false")
    return label, {
        "schema": FUOBJECTARRAY_FIELD_WINDOW_SCHEMA,
        "source": str(path),
        "source_sha256": core_pack.sha256_file(path),
        "status": payload["status"],
        "same_base_flow": same_base_flow,
        "required_fields": fields,
        "sources": payload.get("sources"),
        "consumption_scope": contract.get("consumption_scope"),
        "clears_blocker": FIELD_WINDOW_BLOCKER,
    }


def static_artifact_provenance_blockers(commands: dict[str, object]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for artifact_name, record in commands.items():
        if not isinstance(record, dict):
            continue
        provenance = record.get("provenance")
        if not isinstance(provenance, dict) or not provenance.get("verified"):
            blockers.append(
                {
                    "reason": "unverified_static_artifact_provenance",
                    "artifact": artifact_name,
                    "detail": provenance.get("reason") if isinstance(provenance, dict) else "missing_provenance_record",
                }
            )
    return blockers


def promotion_gate(candidates: list[dict[str, object]], commands: dict[str, object]) -> dict[str, object]:
    blockers = [{"reason": "static_only_evidence", "detail": "Static evidence does not promote runtime globals alone."}]
    blockers.extend(static_artifact_provenance_blockers(commands))
    for candidate in candidates:
        contract = candidate.get("static_contract")
        if isinstance(contract, dict) and contract.get("blockers"):
            blockers.append(
                {
                    "reason": "candidate_static_contract_blocked",
                    "candidate": candidate.get("label"),
                    "blockers": contract.get("blockers"),
                }
            )
    return {"ready": False, "blockers": blockers}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.expanduser().resolve()
    reject_protected_path(output_dir, "--output-dir")
    core_pack.require_ignored_output_path(output_dir, "--output-dir")
    reject_protected_path(args.binary, "--binary")
    for label, path in (
        ("--readelf-programs", args.readelf_programs),
        ("--readelf-sections", args.readelf_sections),
        ("--objdump", args.objdump),
    ):
        if path is not None:
            reject_protected_path(path, label)
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = args.binary.expanduser().resolve()
    binary_sha256 = core_pack.sha256_file(binary)
    field_window_evidence: dict[str, dict[str, object]] = {}
    for path in args.fuobjectarray_field_window_evidence or []:
        label, evidence = load_fuobjectarray_field_window_evidence(path, binary_sha256)
        field_window_evidence[label] = evidence
    kind_overrides = dict(args.candidate_kind or [])
    candidates = validate_candidates(args.candidate, kind_overrides)
    target_map = static_xref_targets(candidates, kind_overrides)

    commands: dict[str, object] = {}
    commands["readelf_programs"] = copy_or_generate_artifact(
        source=args.readelf_programs.expanduser().resolve() if args.readelf_programs else None,
        command=["readelf", "-l", "-W", str(binary)],
        output_path=output_dir / "ShooterGameServer.readelf-programs.txt",
        binary_sha256=binary_sha256,
        artifact_kind="readelf_programs",
    )
    commands["readelf_sections"] = copy_or_generate_artifact(
        source=args.readelf_sections.expanduser().resolve() if args.readelf_sections else None,
        command=["readelf", "-S", "-W", str(binary)],
        output_path=output_dir / "ShooterGameServer.readelf-sections.txt",
        binary_sha256=binary_sha256,
        artifact_kind="readelf_sections",
    )
    commands["objdump"] = copy_or_generate_artifact(
        source=args.objdump.expanduser().resolve() if args.objdump else None,
        command=["objdump", "-d", "-M", "intel", str(binary)],
        output_path=output_dir / "ShooterGameServer.objdump",
        binary_sha256=binary_sha256,
        artifact_kind="objdump",
    )
    for record in commands.values():
        if isinstance(record, dict):
            core_pack.require_success(record)

    segments = parse_readelf_segments(output_dir / "ShooterGameServer.readelf-programs.txt")
    sections = parse_readelf_sections(output_dir / "ShooterGameServer.readelf-sections.txt")
    xrefs_payload = enrich_xrefs_with_ranges(
        core_pack.collect_static_xrefs(output_dir / "ShooterGameServer.objdump", target_map),
        segments=segments,
        sections=sections,
    )
    xrefs_path = output_dir / "static-global-xrefs.json"
    xrefs_path.write_text(json.dumps(xrefs_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    candidate_records = [
        candidate_payload(
            label=label,
            address=address,
            kind_overrides=kind_overrides,
            segments=segments,
            sections=sections,
            xrefs_payload=xrefs_payload,
            field_window_evidence=field_window_evidence,
        )
        for label, address in candidates
    ]

    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "obelisk_commit": core_pack.detect_obelisk_commit(Path(__file__).resolve().parents[1]),
        "binary": {
            "path": str(binary),
            "sha256": binary_sha256,
        },
        "commands": commands,
        "artifacts": {
            "readelf_programs": str(output_dir / "ShooterGameServer.readelf-programs.txt"),
            "readelf_sections": str(output_dir / "ShooterGameServer.readelf-sections.txt"),
            "objdump": str(output_dir / "ShooterGameServer.objdump"),
            "static_xrefs": str(xrefs_path),
        },
        "candidates": candidate_records,
        "promotion_gate": promotion_gate(candidate_records, commands),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="ShooterGameServer ELF binary.")
    parser.add_argument("--candidate", action="append", required=True, help="Candidate global as LABEL=ADDR.")
    parser.add_argument(
        "--candidate-kind",
        action="append",
        type=parse_candidate_kind,
        help="Explicit candidate kind as LABEL=gobjects or LABEL=fname_root for ambiguous labels.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for static evidence artifacts.")
    parser.add_argument("--objdump", type=Path, help="Existing objdump -d -M intel text to copy instead of running objdump.")
    parser.add_argument("--readelf-programs", type=Path, help="Existing readelf -l -W text to copy.")
    parser.add_argument("--readelf-sections", type=Path, help="Existing readelf -S -W text to copy.")
    parser.add_argument(
        "--fuobjectarray-field-window-evidence",
        action="append",
        type=Path,
        help="Redacted FUObjectArray field-window evidence JSON to consume for internal static research.",
    )
    parser.add_argument("--json", action="store_true", help="Print manifest JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not shutil.which("readelf") and (not args.readelf_programs or not args.readelf_sections):
        raise SystemExit("readelf is required unless --readelf-programs and --readelf-sections are provided")
    if not shutil.which("objdump") and not args.objdump:
        raise SystemExit("objdump is required unless --objdump is provided")
    payload = build_payload(args)
    manifest_path = args.output_dir.expanduser().resolve() / "manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
