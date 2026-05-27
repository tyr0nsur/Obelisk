#!/usr/bin/env python3
"""Inspect candidate UFunction/UStruct fields from an offline ELF core dump.

This tool is intentionally conservative: it labels observed offsets as candidates, keeps
reject reasons beside every interpreted value, and never promotes a layout as definitive.
It reads an existing core file only and never attaches to a running process.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402


DEFAULT_WINDOW_SIZE = 0xC0
DEFAULT_MAX_OBJECT_SCAN = 30000
POINTER_ALIGNMENT = 8


@dataclass(frozen=True)
class FieldSpec:
    label: str
    offset: int
    kind: str
    family: str
    validator: Callable[[int], list[str]]


def parse_int(value: str) -> int:
    return int(value, 0)


def hex_or_none(value: int | None) -> str | None:
    return None if value is None else f"0x{value:x}"


def parse_hex_string(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    return int(value, 16)


def read_int(memory: uobjects.CoreMemory, address: int, fmt: str) -> int | None:
    size = struct.calcsize(fmt)
    data = memory.read(address, size)
    return None if data is None else struct.unpack(fmt, data)[0]


def read_u16(memory: uobjects.CoreMemory, address: int) -> int | None:
    return read_int(memory, address, "<H")


def read_i16(memory: uobjects.CoreMemory, address: int) -> int | None:
    return read_int(memory, address, "<h")


def read_i32(memory: uobjects.CoreMemory, address: int) -> int | None:
    return read_int(memory, address, "<i")


def read_u32(memory: uobjects.CoreMemory, address: int) -> int | None:
    return read_int(memory, address, "<I")


def plausible_nonzero_u32(value: int) -> list[str]:
    return ["zero_value"] if value == 0 else []


def plausible_index(value: int) -> list[str]:
    reasons: list[str] = []
    if value < 0:
        reasons.append("negative_index")
    if value > 10_000_000:
        reasons.append("implausibly_large_index")
    return reasons


def plausible_small_count(value: int) -> list[str]:
    if value > 4096:
        return ["implausibly_large_count"]
    return []


def plausible_size(value: int) -> list[str]:
    if value > 0x10000:
        return ["implausibly_large_size"]
    return []


def plausible_alignment(value: int) -> list[str]:
    if value <= 0:
        return ["non_positive_alignment"]
    if value > 0x1000:
        return ["implausibly_large_alignment"]
    if value & (value - 1):
        return ["not_power_of_two"]
    return []


def plausible_offset16(value: int) -> list[str]:
    if value not in (0xFFFF, 0xFFFE) and value > 0x8000:
        return ["implausibly_large_offset"]
    return []


def always_candidate(_value: int) -> list[str]:
    return []


FIELD_SPECS = [
    FieldSpec("uobject.object_flags", 0x08, "u32", "UObjectBase", always_candidate),
    FieldSpec("uobject.internal_index", 0x0C, "i32", "UObjectBase", plausible_index),
    FieldSpec("uobject.name_index", 0x18, "i32", "UObjectBase", plausible_index),
    FieldSpec("uobject.name_number", 0x1C, "i32", "UObjectBase", plausible_index),
    FieldSpec("uproperty.array_dim", 0x30, "i32", "UProperty", plausible_small_count),
    FieldSpec("uproperty.element_size", 0x34, "i32", "UProperty", plausible_size),
    FieldSpec("uproperty.property_flags_low", 0x38, "u32", "UProperty", always_candidate),
    FieldSpec("uproperty.property_flags_high", 0x3C, "u32", "UProperty", always_candidate),
    FieldSpec("uproperty.offset_internal", 0x4C, "i32", "UProperty", plausible_size),
    FieldSpec("ustruct.properties_size", 0x40, "i32", "UStruct", plausible_size),
    FieldSpec("ustruct.min_alignment", 0x44, "i32", "UStruct", plausible_alignment),
    FieldSpec("ufunction.function_flags", 0x90, "u32", "UFunction", plausible_nonzero_u32),
    FieldSpec("ufunction.rep_offset", 0x94, "u16", "UFunction", plausible_offset16),
    FieldSpec("ufunction.num_parms", 0x96, "u16", "UFunction", plausible_small_count),
    FieldSpec("ufunction.parms_size", 0x98, "u16", "UFunction", plausible_size),
    FieldSpec("ufunction.return_value_offset", 0x9A, "u16", "UFunction", plausible_offset16),
    FieldSpec("ufunction.rpc_id", 0x9C, "u16", "UFunction", always_candidate),
    FieldSpec("ufunction.rpc_response_id", 0x9E, "u16", "UFunction", always_candidate),
]

POINTER_LABELS = {
    0x10: "uobject.class",
    0x20: "uobject.outer",
    0x28: "ufield.next",
    0x30: "ustruct.super_struct",
    0x38: "ustruct.children",
    0x48: "ustruct.property_link_or_script_data",
    0x50: "uproperty.property_link_next_or_ustruct.child_properties",
    0x58: "ustruct.property_link_or_destructor_link",
    0x60: "ustruct.ref_link_or_post_construct_link",
    0x98: "ufunction.first_property_to_init",
    0xA0: "ufunction.event_graph_function",
    0xA8: "ufunction.native_func_candidate",
    0xB0: "ufunction.trailing_pointer_candidate",
}


class GObjectContext:
    def __init__(
        self,
        memory: uobjects.CoreMemory,
        *,
        gobjects: int,
        fname_root_slot: int,
        max_object_scan: int,
    ) -> None:
        self.memory = memory
        self.gobjects = gobjects
        self.fname_root_slot = fname_root_slot
        self.max_object_scan = max_object_scan
        self.chunks = memory.read_ptr(gobjects + uobjects.GOBJECTS_CHUNKS_OFFSET)
        self.object_count = read_i32(memory, gobjects + uobjects.GOBJECTS_COUNT_OFFSET)
        self.fname_table = memory.read_ptr(fname_root_slot)
        self._address_to_index: dict[int, int] | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "gobjects": hex_or_none(self.gobjects),
            "fname_root_slot": hex_or_none(self.fname_root_slot),
            "fname_table": hex_or_none(self.fname_table),
            "chunks": hex_or_none(self.chunks),
            "object_count": self.object_count,
            "max_object_scan": self.max_object_scan,
        }

    def object_address_for_index(self, index: int) -> int | None:
        if self.chunks is None or self.object_count is None:
            return None
        if index < 0 or index >= self.object_count:
            return None
        chunk_index = index // uobjects.GOBJECTS_CHUNK_SIZE
        index_in_chunk = index % uobjects.GOBJECTS_CHUNK_SIZE
        chunk = self.memory.read_ptr(self.chunks + chunk_index * 8)
        if not chunk:
            return None
        item = chunk + index_in_chunk * uobjects.FUOBJECT_ITEM_SIZE
        return self.memory.read_ptr(item)

    def address_to_index(self) -> dict[int, int]:
        if self._address_to_index is not None:
            return self._address_to_index
        mapping: dict[int, int] = {}
        if self.object_count is not None:
            limit = min(max(self.max_object_scan, 0), self.object_count)
            for index in range(limit):
                address = self.object_address_for_index(index)
                if address:
                    mapping.setdefault(address, index)
        self._address_to_index = mapping
        return mapping

    def describe_uobject(self, address: int) -> dict[str, object] | None:
        return uobjects.read_uobject(self.memory, address, self.fname_table)

    def index_for_address(self, address: int) -> int | None:
        return self.address_to_index().get(address)

    def resolve_uobject_pointer(self, address: int | None) -> dict[str, object]:
        reject_reasons: list[str] = []
        gobjects_index: int | None = None
        if address is None:
            return {"status": "rejected", "reject_reasons": ["unreadable_pointer_value"]}
        if address == 0:
            return {"status": "rejected", "reject_reasons": ["null_pointer"]}
        if self.memory.segment_for_vaddr(address, 1) is None:
            return {
                "status": "rejected",
                "reject_reasons": ["pointer_target_not_in_core_segments"],
            }

        summary = self.describe_uobject(address)
        if summary is None:
            return {
                "status": "candidate-readable-pointer",
                "reject_reasons": ["not_readable_as_uobject_base"],
            }

        if summary.get("name") is None:
            reject_reasons.append("unresolved_object_name")
        if summary.get("class_name") is None:
            reject_reasons.append("unresolved_class_name")

        internal_index = summary.get("internal_index")
        if not isinstance(internal_index, int):
            reject_reasons.append("missing_internal_index")
        elif internal_index < 0:
            reject_reasons.append("negative_internal_index")
        elif self.object_count is not None and internal_index >= self.object_count:
            reject_reasons.append("internal_index_outside_gobjects_count")
        else:
            indexed_address = self.object_address_for_index(internal_index)
            if indexed_address is None:
                reject_reasons.append("gobjects_index_unreadable")
            elif indexed_address != address:
                reject_reasons.append("gobjects_internal_index_mismatch")
            else:
                gobjects_index = internal_index

        status = "candidate-uobject" if not reject_reasons else "rejected"
        return {
            "status": status,
            "reject_reasons": reject_reasons,
            "uobject": summary,
            "gobjects_index": gobjects_index,
        }


def inspect_scalar_field(memory: uobjects.CoreMemory, object_address: int, spec: FieldSpec) -> dict[str, object]:
    absolute = object_address + spec.offset
    if spec.kind == "u16":
        value = read_u16(memory, absolute)
    elif spec.kind == "i16":
        value = read_i16(memory, absolute)
    elif spec.kind == "u32":
        value = read_u32(memory, absolute)
    elif spec.kind == "i32":
        value = read_i32(memory, absolute)
    else:
        raise ValueError(f"unsupported field kind: {spec.kind}")

    if value is None:
        reject_reasons = ["unreadable_field"]
        status = "rejected"
    else:
        reject_reasons = spec.validator(value)
        status = "candidate" if not reject_reasons else "rejected"

    return {
        "label": spec.label,
        "family": spec.family,
        "offset": f"0x{spec.offset:x}",
        "absolute": f"0x{absolute:x}",
        "kind": spec.kind,
        "value": value,
        "value_hex": hex_or_none(value),
        "status": status,
        "reject_reasons": reject_reasons,
    }


def inspect_pointer_slot(context: GObjectContext, object_address: int, offset: int) -> dict[str, object]:
    absolute = object_address + offset
    value = context.memory.read_ptr(absolute)
    label = POINTER_LABELS.get(offset, "aligned_pointer_slot")
    if label == "ufunction.native_func_candidate" and value:
        segment = context.memory.segment_for_vaddr(value, 1)
        if segment is not None and segment.flags & 0x1:
            return {
                "label": label,
                "offset": f"0x{offset:x}",
                "absolute": f"0x{absolute:x}",
                "kind": "ptr",
                "value": hex_or_none(value),
                "status": "candidate-code-pointer",
                "reject_reasons": [],
                "segment_flags": segment.flags,
            }
    resolved = context.resolve_uobject_pointer(value)
    result = {
        "label": label,
        "offset": f"0x{offset:x}",
        "absolute": f"0x{absolute:x}",
        "kind": "ptr",
        "value": hex_or_none(value),
        "status": resolved["status"],
        "reject_reasons": resolved["reject_reasons"],
    }
    if "uobject" in resolved:
        result["resolved_uobject"] = resolved["uobject"]
    if resolved.get("gobjects_index") is not None:
        result["gobjects_index"] = resolved["gobjects_index"]
    return result


def inspect_integer_slot(memory: uobjects.CoreMemory, object_address: int, offset: int) -> dict[str, object]:
    absolute = object_address + offset
    raw = memory.read(absolute, 8)
    if raw is None:
        return {
            "offset": f"0x{offset:x}",
            "absolute": f"0x{absolute:x}",
            "status": "rejected",
            "reject_reasons": ["unreadable_window_slot"],
        }
    u32_low, u32_high = struct.unpack("<II", raw)
    i32_low, i32_high = struct.unpack("<ii", raw)
    return {
        "offset": f"0x{offset:x}",
        "absolute": f"0x{absolute:x}",
        "u32_low": u32_low,
        "u32_low_hex": f"0x{u32_low:x}",
        "i32_low": i32_low,
        "u32_high": u32_high,
        "u32_high_hex": f"0x{u32_high:x}",
        "i32_high": i32_high,
        "status": "observed",
        "reject_reasons": [],
    }


def read_u64(memory: uobjects.CoreMemory, address: int) -> int | None:
    return read_int(memory, address, "<Q")


def membership_fields(resolved: dict[str, object], prefix: str = "") -> dict[str, object]:
    return {
        f"{prefix}membership_status": resolved["status"],
        f"{prefix}membership_reject_reasons": resolved["reject_reasons"],
        f"{prefix}gobjects_index": resolved.get("gobjects_index"),
    }


def inspect_enum_candidate(context: GObjectContext, property_address: int) -> dict[str, object]:
    enum_address = context.memory.read_ptr(property_address + 0x70)
    if not enum_address:
        return {
            "status": "rejected",
            "reject_reasons": ["null_enum_pointer"],
            "enum": None,
        }

    names_address = context.memory.read_ptr(enum_address + 0x40)
    count = read_i32(context.memory, enum_address + 0x48)
    reject_reasons: list[str] = []
    if not names_address:
        reject_reasons.append("null_enum_names")
    if count is None:
        reject_reasons.append("unreadable_enum_count")
    elif count < 0 or count > 64:
        reject_reasons.append("implausible_enum_count")

    values: list[dict[str, object]] = []
    if names_address and count is not None and 0 <= count <= 64:
        for index in range(count):
            raw = context.memory.read(names_address + index * 8, 8)
            if raw is None:
                values.append({"index": index, "name_index": None, "name": None})
                reject_reasons.append(f"enum_name_{index}_unreadable")
                continue
            name_index, name_number = struct.unpack("<ii", raw)
            resolved = uobjects.resolve_fname(context.memory, context.fname_table, name_index, name_number)
            values.append(
                {
                    "index": index,
                    "name_index": name_index,
                    "name_number": name_number,
                    "name": resolved.text,
                }
            )
            if resolved.text is None:
                reject_reasons.append(f"enum_name_{index}_unresolved")

    return {
        "status": "candidate" if not reject_reasons else "rejected",
        "reject_reasons": reject_reasons,
        "enum": hex_or_none(enum_address),
        "names": hex_or_none(names_address),
        "count": count,
        "values": values,
    }


def inspect_array_inner_candidate(context: GObjectContext, property_address: int) -> dict[str, object]:
    inner_address = context.memory.read_ptr(property_address + 0x70)
    if not inner_address:
        return {
            "status": "rejected",
            "reject_reasons": ["null_inner_pointer"],
            "inner": None,
        }

    resolved_inner = context.resolve_uobject_pointer(inner_address)
    inner_summary = summarize_uobject(resolved_inner.get("uobject"))
    if inner_summary is not None:
        inner_summary["object_index"] = resolved_inner.get("gobjects_index")
    return {
        "status": "candidate"
        if resolved_inner["status"] == "candidate-uobject"
        else "rejected",
        "reject_reasons": resolved_inner["reject_reasons"],
        "inner": hex_or_none(inner_address),
        "inner_property": inner_summary,
        "membership_status": resolved_inner["status"],
    }


def inspect_struct_type_candidate(context: GObjectContext, property_address: int) -> dict[str, object]:
    struct_address = context.memory.read_ptr(property_address + 0x70)
    if not struct_address:
        return {
            "status": "rejected",
            "reject_reasons": ["null_struct_pointer"],
            "struct": None,
        }

    resolved_struct = context.resolve_uobject_pointer(struct_address)
    struct_summary = summarize_uobject(resolved_struct.get("uobject"))
    if struct_summary is not None:
        struct_summary["object_index"] = resolved_struct.get("gobjects_index")
    return {
        "status": "candidate"
        if resolved_struct["status"] == "candidate-uobject"
        else "rejected",
        "reject_reasons": resolved_struct["reject_reasons"],
        "struct": hex_or_none(struct_address),
        "struct_type": struct_summary,
        "membership_status": resolved_struct["status"],
    }


def inspect_property_chain(
    context: GObjectContext,
    *,
    owner_address: int,
    first_property: int | None,
    expected_count: int | None,
    parms_size: int | None,
    max_depth: int = 64,
) -> dict[str, object]:
    properties: list[dict[str, object]] = []
    reject_reasons: list[str] = []
    seen: set[int] = set()
    current = first_property

    for depth in range(max_depth):
        if not current:
            break
        if current in seen:
            reject_reasons.append("property_chain_loop")
            break
        seen.add(current)

        resolved_property = context.resolve_uobject_pointer(current)
        summary = resolved_property.get("uobject")
        if not isinstance(summary, dict):
            reject_reasons.append(f"property_{depth}_not_readable_as_uobject")
            break

        property_rejects: list[str] = []
        if resolved_property["status"] != "candidate-uobject":
            property_rejects.extend(
                f"membership_{reason}" for reason in resolved_property["reject_reasons"]
            )

        owner = summary.get("outer")
        owner_matches = owner == f"0x{owner_address:x}"
        if not owner_matches:
            reject_reasons.append(f"property_{depth}_outer_mismatch")
            property_rejects.append("outer_mismatch")

        class_address = parse_hex_string(summary.get("class"))
        resolved_class = context.resolve_uobject_pointer(class_address)
        if resolved_class["status"] != "candidate-uobject":
            property_rejects.extend(
                f"class_membership_{reason}" for reason in resolved_class["reject_reasons"]
            )

        outer_address = parse_hex_string(summary.get("outer"))
        resolved_outer = context.resolve_uobject_pointer(outer_address)
        if resolved_outer["status"] != "candidate-uobject":
            property_rejects.extend(
                f"outer_membership_{reason}" for reason in resolved_outer["reject_reasons"]
            )

        array_dim = read_i32(context.memory, current + 0x30)
        element_size = read_i32(context.memory, current + 0x34)
        property_flags = read_u64(context.memory, current + 0x38)
        offset_internal = read_i32(context.memory, current + 0x4C)
        next_field = context.memory.read_ptr(current + 0x28)
        next_property = context.memory.read_ptr(current + 0x50)

        if array_dim is None or array_dim <= 0 or array_dim > 4096:
            property_rejects.append("implausible_array_dim")
        if element_size is None or element_size <= 0 or element_size > 0x10000:
            property_rejects.append("implausible_element_size")
        if offset_internal is None or offset_internal < 0:
            property_rejects.append("implausible_offset_internal")
        if (
            parms_size is not None
            and offset_internal is not None
            and element_size is not None
            and offset_internal + element_size > parms_size
        ):
            property_rejects.append("property_exceeds_parms_size")

        property_payload = {
            "depth": depth,
            "address": f"0x{current:x}",
            "summary": summary,
            "owner_matches": owner_matches,
            "array_dim": array_dim,
            "element_size": element_size,
            "property_flags": hex_or_none(property_flags),
            "offset_internal": offset_internal,
            "offset_internal_hex": hex_or_none(offset_internal),
            "next_field": hex_or_none(next_field),
            "next_property": hex_or_none(next_property),
            **membership_fields(resolved_property),
            **membership_fields(resolved_class, "class_"),
            **membership_fields(resolved_outer, "outer_"),
            "class_summary": resolved_class.get("uobject"),
            "outer_summary": resolved_outer.get("uobject"),
            "status": "candidate" if not property_rejects else "rejected",
            "reject_reasons": property_rejects,
        }
        if summary.get("class_name") == "ByteProperty":
            property_payload["enum_candidate"] = inspect_enum_candidate(context, current)
        if summary.get("class_name") == "ArrayProperty":
            property_payload["array_inner_candidate"] = inspect_array_inner_candidate(context, current)
        if summary.get("class_name") == "StructProperty":
            property_payload["struct_type_candidate"] = inspect_struct_type_candidate(context, current)
        properties.append(property_payload)
        if property_rejects:
            reject_reasons.append(f"property_{depth}_rejected")
        current = next_field

    if current:
        reject_reasons.append("property_chain_depth_limit")
    if expected_count is not None and len(properties) != expected_count:
        reject_reasons.append("property_count_mismatch")

    return {
        "first_property": hex_or_none(first_property),
        "expected_count": expected_count,
        "observed_count": len(properties),
        "parms_size": parms_size,
        "status": "candidate" if not reject_reasons else "rejected",
        "reject_reasons": reject_reasons,
        "properties": properties,
    }


def inspect_target(
    context: GObjectContext,
    *,
    target_kind: str,
    target_value: int,
    object_address: int | None,
    window_size: int,
    inspection_mode: str,
) -> dict[str, object]:
    target = {
        "target_kind": target_kind,
        "target_value": target_value if target_kind == "index" else f"0x{target_value:x}",
        "object": hex_or_none(object_address),
    }
    if object_address is None:
        target.update(
            {
                "status": "rejected",
                "reject_reasons": ["target_object_not_found"],
                "object_summary": None,
                "candidate_fields": [],
                "pointer_window": [],
                "integer_window": [],
            }
        )
        return target

    resolved = context.resolve_uobject_pointer(object_address)
    object_summary = resolved.get("uobject")
    reject_reasons = list(resolved["reject_reasons"])
    class_name = object_summary.get("class_name") if isinstance(object_summary, dict) else None
    if inspection_mode == "script-struct":
        if class_name != "ScriptStruct":
            reject_reasons.append("class_name_not_script_struct")
    elif inspection_mode == "ufunction":
        if class_name != "Function":
            reject_reasons.append("class_name_not_function")
    elif class_name not in ("Function", "ScriptStruct"):
        reject_reasons.append("class_name_not_function_or_script_struct")

    target["status"] = "candidate" if not reject_reasons else "rejected"
    target["reject_reasons"] = reject_reasons
    target["object_summary"] = object_summary
    target["object_index"] = resolved.get("gobjects_index")
    target.update(membership_fields(resolved, "object_"))
    target["class_summary"] = None
    target["class_index"] = None
    target["class_membership_status"] = None
    target["class_membership_reject_reasons"] = []
    target["outer_summary"] = None
    target["outer_index"] = None
    target["outer_membership_status"] = None
    target["outer_membership_reject_reasons"] = []
    if isinstance(object_summary, dict):
        class_address = parse_hex_string(object_summary.get("class"))
        if class_address is not None:
            resolved_class = context.resolve_uobject_pointer(class_address)
            target["class_summary"] = resolved_class.get("uobject")
            target["class_index"] = resolved_class.get("gobjects_index")
            target["class_membership_status"] = resolved_class["status"]
            target["class_membership_reject_reasons"] = resolved_class["reject_reasons"]
        outer_address = parse_hex_string(object_summary.get("outer"))
        if outer_address is not None:
            resolved_outer = context.resolve_uobject_pointer(outer_address)
            target["outer_summary"] = resolved_outer.get("uobject")
            target["outer_index"] = resolved_outer.get("gobjects_index")
            target["outer_membership_status"] = resolved_outer["status"]
            target["outer_membership_reject_reasons"] = resolved_outer["reject_reasons"]

    field_specs = [spec for spec in FIELD_SPECS if spec.offset < window_size]
    target["candidate_fields"] = [inspect_scalar_field(context.memory, object_address, spec) for spec in field_specs]
    first_property = context.memory.read_ptr(object_address + 0x38)
    is_script_struct = class_name == "ScriptStruct"
    expected_count = None if is_script_struct else read_u16(context.memory, object_address + 0x96)
    parms_size = read_i32(context.memory, object_address + 0x40) if is_script_struct else read_u16(context.memory, object_address + 0x98)
    target["inspection_mode"] = "script_struct" if is_script_struct else "ufunction"
    target["num_parms"] = expected_count
    target["parms_size"] = parms_size
    target["property_chain"] = inspect_property_chain(
        context,
        owner_address=object_address,
        first_property=first_property,
        expected_count=expected_count,
        parms_size=parms_size,
    )
    target["pointer_window"] = [
        inspect_pointer_slot(context, object_address, offset)
        for offset in range(0, window_size, POINTER_ALIGNMENT)
    ]
    target["integer_window"] = [
        inspect_integer_slot(context.memory, object_address, offset)
        for offset in range(0, window_size, POINTER_ALIGNMENT)
    ]
    return target


def inspect_core(
    memory: uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    object_addresses: Iterable[int],
    indices: Iterable[int],
    name_contains: Iterable[str] = (),
    outer_contains: Iterable[str] = (),
    name_exact: Iterable[str] = (),
    outer_exact: Iterable[str] = (),
    window_size: int,
    max_object_scan: int,
    inspection_mode: str = "auto",
) -> dict[str, object]:
    context = GObjectContext(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_object_scan=max_object_scan,
    )
    targets: list[dict[str, object]] = []
    seen_addresses: set[int] = set()
    for index in indices:
        object_address = context.object_address_for_index(index)
        if object_address is not None:
            seen_addresses.add(object_address)
        targets.append(
            inspect_target(
                context,
                target_kind="index",
                target_value=index,
                object_address=object_address,
                window_size=window_size,
                inspection_mode=inspection_mode,
            )
        )
    for address in object_addresses:
        seen_addresses.add(address)
        targets.append(
            inspect_target(
                context,
                target_kind="address",
                target_value=address,
                object_address=address,
                window_size=window_size,
                inspection_mode=inspection_mode,
            )
        )
    for index, address in find_matching_function_indices(
        context,
        name_contains=name_contains,
        outer_contains=outer_contains,
        name_exact=name_exact,
        outer_exact=outer_exact,
    ):
        if address in seen_addresses:
            continue
        seen_addresses.add(address)
        targets.append(
            inspect_target(
                context,
                target_kind="index",
                target_value=index,
                object_address=address,
                window_size=window_size,
                inspection_mode=inspection_mode,
            )
        )

    return {
        "metadata": context.metadata(),
        "interpretation": {
            "status": "candidate-only",
            "note": "Offsets are candidate observations from this core, not accepted UE4 layout contracts.",
        },
        "targets": targets,
    }


def summarize_uobject(summary: object) -> dict[str, object] | None:
    if not isinstance(summary, dict):
        return None
    return {
        "name": summary.get("name"),
        "name_index": summary.get("name_index"),
        "class_name": summary.get("class_name"),
    }


def scalar_field_value(target: dict[str, object], label: str) -> object:
    for field in target.get("candidate_fields", []):
        if isinstance(field, dict) and field.get("label") == label:
            return field.get("value_hex") if field.get("kind") in ("u32", "u16") else field.get("value")
    return None


def build_fixture_snapshot(
    payload: dict[str, object],
    *,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    modes = {
        target.get("inspection_mode")
        for target in payload.get("targets", [])
        if isinstance(target, dict)
    }
    if len(modes) > 1:
        raise ValueError("--snapshot-json requires targets with a single inspection_mode")
    mode = next(iter(modes), "ufunction")
    if mode not in ("ufunction", "script_struct"):
        mode = "ufunction"
    schema = (
        "obelisk.scriptstruct-chain.snapshot.v1"
        if mode == "script_struct"
        else "obelisk.ufunction-chain.snapshot.v1"
    )
    snapshot_targets: list[dict[str, object]] = []
    for target in payload.get("targets", []):
        if not isinstance(target, dict):
            continue
        target_summary = summarize_uobject(target.get("object_summary"))
        outer_summary = summarize_uobject(target.get("outer_summary"))
        chain = target.get("property_chain") if isinstance(target.get("property_chain"), dict) else {}

        properties: list[dict[str, object]] = []
        for prop in chain.get("properties", []) if isinstance(chain, dict) else []:
            if not isinstance(prop, dict):
                continue
            prop_summary = summarize_uobject(prop.get("summary")) or {}
            property_payload: dict[str, object] = {
                "depth": prop.get("depth"),
                "object_index": prop.get("gobjects_index"),
                "name": prop_summary.get("name"),
                "name_index": prop_summary.get("name_index"),
                "class_name": prop_summary.get("class_name"),
                "class_name_index": (prop.get("class_summary") or {}).get("name_index")
                if isinstance(prop.get("class_summary"), dict)
                else None,
                "class_object_index": prop.get("class_gobjects_index"),
                "offset_internal": prop.get("offset_internal"),
                "element_size": prop.get("element_size"),
                "array_dim": prop.get("array_dim"),
                "property_flags": prop.get("property_flags"),
                "membership_status": prop.get("membership_status"),
                "class_membership_status": prop.get("class_membership_status"),
                "outer_membership_status": prop.get("outer_membership_status"),
                "status": prop.get("status"),
                "reject_reasons": prop.get("reject_reasons", []),
            }
            enum_candidate = prop.get("enum_candidate")
            if isinstance(enum_candidate, dict):
                property_payload["enum_candidate"] = {
                    "status": enum_candidate.get("status"),
                    "reject_reasons": enum_candidate.get("reject_reasons", []),
                    "values": [
                        item.get("name")
                        for item in enum_candidate.get("values", [])
                        if isinstance(item, dict)
                    ],
                }
            array_inner_candidate = prop.get("array_inner_candidate")
            if isinstance(array_inner_candidate, dict):
                property_payload["array_inner_candidate"] = {
                    "status": array_inner_candidate.get("status"),
                    "reject_reasons": array_inner_candidate.get("reject_reasons", []),
                    "membership_status": array_inner_candidate.get("membership_status"),
                    "inner_property": array_inner_candidate.get("inner_property"),
                }
            struct_type_candidate = prop.get("struct_type_candidate")
            if isinstance(struct_type_candidate, dict):
                property_payload["struct_type_candidate"] = {
                    "status": struct_type_candidate.get("status"),
                    "reject_reasons": struct_type_candidate.get("reject_reasons", []),
                    "membership_status": struct_type_candidate.get("membership_status"),
                    "struct_type": struct_type_candidate.get("struct_type"),
                }
            properties.append(property_payload)

        snapshot_target = {
            "target": {
                "kind": target.get("target_kind"),
                "value": target.get("target_value"),
                "object_index": target.get("object_index"),
                "name": target_summary.get("name") if target_summary else None,
                "name_index": target_summary.get("name_index") if target_summary else None,
                "class_name": target_summary.get("class_name") if target_summary else None,
                "class_name_index": (target.get("class_summary") or {}).get("name_index")
                if isinstance(target.get("class_summary"), dict)
                else None,
                "class_object_index": target.get("class_index"),
                "outer_name": outer_summary.get("name") if outer_summary else None,
                "outer_name_index": outer_summary.get("name_index") if outer_summary else None,
                "outer_class_name": outer_summary.get("class_name") if outer_summary else None,
                "outer_object_index": target.get("outer_index"),
            },
            "inspection_mode": target.get("inspection_mode"),
            "status": target.get("status"),
            "reject_reasons": target.get("reject_reasons", []),
            "membership": {
                "target": target.get("object_membership_status"),
                "class": target.get("class_membership_status"),
                "outer": target.get("outer_membership_status"),
            },
            "property_chain": {
                "status": chain.get("status") if isinstance(chain, dict) else None,
                "reject_reasons": chain.get("reject_reasons", []) if isinstance(chain, dict) else [],
                "expected_count": chain.get("expected_count") if isinstance(chain, dict) else None,
                "observed_count": chain.get("observed_count") if isinstance(chain, dict) else None,
                "properties": properties,
            },
        }
        if mode == "script_struct":
            snapshot_target["properties_size"] = target.get("parms_size")
            snapshot_target["min_alignment"] = scalar_field_value(target, "ustruct.min_alignment")
            snapshot_target["property_chain"]["properties_size"] = chain.get("parms_size") if isinstance(chain, dict) else None
        else:
            snapshot_target["num_parms"] = target.get("num_parms")
            snapshot_target["parms_size"] = target.get("parms_size")
            snapshot_target["function_flags"] = scalar_field_value(target, "ufunction.function_flags")
            snapshot_target["return_value_offset"] = scalar_field_value(target, "ufunction.return_value_offset")
            snapshot_target["property_chain"]["parms_size"] = chain.get("parms_size") if isinstance(chain, dict) else None
        snapshot_targets.append(snapshot_target)

    return {
        "schema": schema,
        "evidence": evidence,
        "address_policy": "absolute core paths and addresses omitted; use full inspector JSON for local evidence review",
        "interpretation": payload.get("interpretation"),
        "metadata": {
            "object_count": metadata.get("object_count"),
            "max_object_scan": metadata.get("max_object_scan"),
        },
        "targets": snapshot_targets,
    }


def contains_any(value: object, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack = str(value or "").lower()
    return any(needle in haystack for needle in needles)


def equals_any(value: object, needles: list[str]) -> bool:
    if not needles:
        return True
    haystack = str(value or "").lower()
    return any(haystack == needle for needle in needles)


def find_matching_function_indices(
    context: GObjectContext,
    *,
    name_contains: Iterable[str],
    outer_contains: Iterable[str],
    name_exact: Iterable[str],
    outer_exact: Iterable[str],
) -> list[tuple[int, int]]:
    name_filters = [item.lower() for item in name_contains if item]
    outer_filters = [item.lower() for item in outer_contains if item]
    name_exact_filters = [item.lower() for item in name_exact if item]
    outer_exact_filters = [item.lower() for item in outer_exact if item]
    if not name_filters and not outer_filters and not name_exact_filters and not outer_exact_filters:
        return []
    if context.object_count is None:
        return []

    matches: list[tuple[int, int]] = []
    limit = min(max(context.max_object_scan, 0), context.object_count)
    for index in range(limit):
        address = context.object_address_for_index(index)
        if not address:
            continue
        summary = context.describe_uobject(address)
        if summary is None:
            continue
        class_name = str(summary.get("class_name") or "")
        if class_name not in ("Function", "ScriptStruct"):
            continue
        if not contains_any(summary.get("name"), name_filters):
            continue
        if not equals_any(summary.get("name"), name_exact_filters):
            continue

        outer_name = None
        outer_address = parse_hex_string(summary.get("outer"))
        if outer_address is not None:
            outer_summary = context.describe_uobject(outer_address)
            if isinstance(outer_summary, dict):
                outer_name = outer_summary.get("name")
        if not contains_any(outer_name, outer_filters):
            continue
        if not equals_any(outer_name, outer_exact_filters):
            continue
        matches.append((index, address))
    return matches


def format_text(payload: dict[str, object]) -> str:
    metadata = payload["metadata"]
    lines = [
        "gobjects={gobjects} chunks={chunks} object_count={object_count} "
        "fname_table={fname_table} max_object_scan={max_object_scan}".format(**metadata),
        "interpretation=candidate-only offsets_are_not_definitive",
    ]
    for target in payload["targets"]:
        summary = target.get("object_summary") or {}
        outer_summary = target.get("outer_summary") or {}
        lines.append(
            "target={target_kind}:{target_value} object={object} status={status} "
            "reasons={reasons} object_index={object_index} class={class_name!r} name={name!r} "
            "name_index={name_index} outer={outer} outer_index={outer_index} "
            "outer_name={outer_name!r} outer_name_index={outer_name_index} "
            "object_membership={object_membership} class_membership={class_membership} "
            "outer_membership={outer_membership} "
            "num_parms={num_parms} parms_size={parms_size}".format(
                target_kind=target["target_kind"],
                target_value=target["target_value"],
                object=target["object"],
                status=target["status"],
                reasons=",".join(target["reject_reasons"]) if target["reject_reasons"] else "-",
                object_index=target.get("object_index"),
                class_name=summary.get("class_name") if isinstance(summary, dict) else None,
                name=summary.get("name") if isinstance(summary, dict) else None,
                name_index=summary.get("name_index") if isinstance(summary, dict) else None,
                outer=summary.get("outer") if isinstance(summary, dict) else None,
                outer_index=target.get("outer_index"),
                outer_name=outer_summary.get("name") if isinstance(outer_summary, dict) else None,
                outer_name_index=outer_summary.get("name_index") if isinstance(outer_summary, dict) else None,
                object_membership=target.get("object_membership_status"),
                class_membership=target.get("class_membership_status"),
                outer_membership=target.get("outer_membership_status"),
                num_parms=target.get("num_parms"),
                parms_size=target.get("parms_size"),
            )
        )
        for field in target.get("candidate_fields", []):
            lines.append(
                "  field offset={offset} label={label} kind={kind} value={value_hex} "
                "status={status} reasons={reasons}".format(
                    offset=field["offset"],
                    label=field["label"],
                    kind=field["kind"],
                    value_hex=field["value_hex"],
                    status=field["status"],
                    reasons=",".join(field["reject_reasons"]) if field["reject_reasons"] else "-",
                )
            )
        for pointer in target.get("pointer_window", []):
            if pointer["status"] != "candidate-uobject" and pointer["label"] == "aligned_pointer_slot":
                continue
            resolved = pointer.get("resolved_uobject") or {}
            lines.append(
                "  ptr offset={offset} label={label} value={value} status={status} "
                "reasons={reasons} resolved={class_name!r}/{name!r}".format(
                    offset=pointer["offset"],
                    label=pointer["label"],
                    value=pointer["value"],
                    status=pointer["status"],
                    reasons=",".join(pointer["reject_reasons"]) if pointer["reject_reasons"] else "-",
                    class_name=resolved.get("class_name") if isinstance(resolved, dict) else None,
                    name=resolved.get("name") if isinstance(resolved, dict) else None,
                )
            )
        chain = target.get("property_chain") or {}
        if chain:
            lines.append(
                "  property_chain first={first_property} observed={observed_count} expected={expected_count} "
                "parms_size={parms_size} status={status} reasons={reasons}".format(
                    first_property=chain.get("first_property"),
                    observed_count=chain.get("observed_count"),
                    expected_count=chain.get("expected_count"),
                    parms_size=chain.get("parms_size"),
                    status=chain.get("status"),
                    reasons=",".join(chain.get("reject_reasons", [])) if chain.get("reject_reasons") else "-",
                )
            )
            for prop in chain.get("properties", []):
                prop_summary = prop.get("summary") or {}
                lines.append(
                    "    prop depth={depth} address={address} class={class_name!r} name={name!r} "
                    "offset={offset} element_size={element_size} flags={flags} next={next_field} "
                    "membership={membership} class_membership={class_membership} "
                    "outer_membership={outer_membership} status={status} reasons={reasons}".format(
                        depth=prop["depth"],
                        address=prop["address"],
                        class_name=prop_summary.get("class_name") if isinstance(prop_summary, dict) else None,
                        name=prop_summary.get("name") if isinstance(prop_summary, dict) else None,
                        offset=prop.get("offset_internal_hex"),
                        element_size=prop.get("element_size"),
                        flags=prop.get("property_flags"),
                        next_field=prop.get("next_field"),
                        membership=prop.get("membership_status"),
                        class_membership=prop.get("class_membership_status"),
                        outer_membership=prop.get("outer_membership_status"),
                        status=prop.get("status"),
                        reasons=",".join(prop.get("reject_reasons", [])) if prop.get("reject_reasons") else "-",
                    )
                )
                enum_candidate = prop.get("enum_candidate")
                if isinstance(enum_candidate, dict):
                    enum_values = [
                        str(item.get("name"))
                        for item in enum_candidate.get("values", [])
                        if isinstance(item, dict)
                    ]
                    lines.append(
                        "      enum_candidate enum={enum} count={count} status={status} "
                        "reasons={reasons} values={values}".format(
                            enum=enum_candidate.get("enum"),
                            count=enum_candidate.get("count"),
                            status=enum_candidate.get("status"),
                            reasons=",".join(enum_candidate.get("reject_reasons", []))
                            if enum_candidate.get("reject_reasons")
                            else "-",
                            values=",".join(enum_values),
                        )
                    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline candidate UFunction/UStruct inspection from an ELF core dump."
    )
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing ELF core dump.")
    parser.add_argument("--gobjects", type=parse_int, default=uobjects.DEFAULT_GOBJECTS)
    parser.add_argument("--fname-root-slot", type=parse_int, default=uobjects.DEFAULT_FNAME_ROOT_SLOT)
    parser.add_argument("--object", action="append", type=parse_int, default=[], help="UObject address to inspect.")
    parser.add_argument("--index", action="append", type=parse_int, default=[], help="GObjects index to inspect.")
    parser.add_argument(
        "--name-contains",
        action="append",
        default=[],
        help="Inspect Function/Struct objects whose resolved name contains this substring. Repeatable.",
    )
    parser.add_argument(
        "--outer-contains",
        action="append",
        default=[],
        help="Inspect Function/Struct objects whose resolved outer name contains this substring. Repeatable.",
    )
    parser.add_argument(
        "--name-exact",
        action="append",
        default=[],
        help="Inspect Function/Struct objects whose resolved name exactly matches this value. Repeatable.",
    )
    parser.add_argument(
        "--outer-exact",
        action="append",
        default=[],
        help="Inspect Function/Struct objects whose resolved outer name exactly matches this value. Repeatable.",
    )
    parser.add_argument("--window-size", type=parse_int, default=DEFAULT_WINDOW_SIZE)
    parser.add_argument("--max-object-scan", type=int, default=DEFAULT_MAX_OBJECT_SCAN)
    parser.add_argument(
        "--inspection-mode",
        choices=("auto", "ufunction", "script-struct"),
        default="auto",
        help="Restrict targets to UFunction or ScriptStruct interpretation. Defaults to auto.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--snapshot-json",
        action="store_true",
        help="Emit a sanitized JSON fixture snapshot without core paths or absolute addresses.",
    )
    parser.add_argument("--evidence-ark-sha256", help="ARK binary SHA256 for --snapshot-json evidence metadata.")
    parser.add_argument("--evidence-obelisk-commit", help="Obelisk commit for --snapshot-json evidence metadata.")
    parser.add_argument("--evidence-source", default="offline_core", help="Evidence source label for --snapshot-json.")
    parser.add_argument("--evidence-status", default="candidate-only", help="Evidence status label for --snapshot-json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if (
        not args.object
        and not args.index
        and not args.name_contains
        and not args.outer_contains
        and not args.name_exact
        and not args.outer_exact
    ):
        raise SystemExit(
            "provide at least one --object, --index, --name-contains, --outer-contains, --name-exact, or --outer-exact"
        )
    if args.window_size <= 0:
        raise SystemExit("--window-size must be positive")
    if args.max_object_scan < 0:
        raise SystemExit("--max-object-scan must be non-negative")
    if args.json and args.snapshot_json:
        raise SystemExit("choose only one of --json or --snapshot-json")
    if not args.snapshot_json and (
        args.evidence_ark_sha256 is not None or args.evidence_obelisk_commit is not None
    ):
        raise SystemExit("evidence metadata flags require --snapshot-json")

    memory = uobjects.CoreMemory(args.core)
    try:
        payload = inspect_core(
            memory,
            gobjects=args.gobjects,
            fname_root_slot=args.fname_root_slot,
            object_addresses=args.object,
            indices=args.index,
            name_contains=args.name_contains,
            outer_contains=args.outer_contains,
            name_exact=args.name_exact,
            outer_exact=args.outer_exact,
            window_size=args.window_size,
            max_object_scan=args.max_object_scan,
            inspection_mode=args.inspection_mode,
        )
    finally:
        memory.close()

    if args.json:
        print(json.dumps({"core": str(args.core), **payload}, indent=2, sort_keys=True))
    elif args.snapshot_json:
        evidence = {
            "ark_binary_sha256": args.evidence_ark_sha256,
            "obelisk_commit": args.evidence_obelisk_commit,
            "source": args.evidence_source,
            "status": args.evidence_status,
            "generated_by": "scripts/inspect_core_ufunctions.py --snapshot-json",
        }
        try:
            snapshot = build_fixture_snapshot(payload, evidence=evidence)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
