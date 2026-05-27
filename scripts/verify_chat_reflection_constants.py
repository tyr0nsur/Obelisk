#!/usr/bin/env python3
"""Verify ChatReflection constants against offline core UFunction evidence.

This tool is offline-only: it reads an existing ELF core and local source files. It never
attaches to a running ARK process and never mutates server state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
import inspect_core_ufunctions as inspector  # noqa: E402


CHAT_REFLECTION_SOURCE = REPO_ROOT / "ue" / "ChatReflection.cpp"
DEFAULT_TARGETS = ("ServerChat", "ServerChatTo", "ServerChatToPlayer")


@dataclass(frozen=True)
class FieldSpec:
    field: str
    property_name: str
    name_index_constant: str
    offset: int
    size_constant: str


@dataclass(frozen=True)
class FunctionSpec:
    function: str
    name_index_constant: str
    num_parms: int
    parms_size: int
    fields: tuple[FieldSpec, ...]


@dataclass(frozen=True)
class ChatReflectionSpec:
    constants: dict[str, int]
    functions: dict[str, FunctionSpec]


def parse_int(value: str) -> int:
    return int(value, 0)


def _parse_cpp_int(value: str, constants: dict[str, int]) -> int:
    value = value.strip()
    if value in constants:
        return constants[value]
    return int(value, 0)


def parse_chat_reflection_source(path: Path = CHAT_REFLECTION_SOURCE) -> ChatReflectionSpec:
    text = path.read_text(encoding="utf-8")
    constants: dict[str, int] = {}
    for match in re.finditer(
        r"constexpr\s+(?:int32_t|uint16_t|size_t)\s+"
        r"(?P<name>k[A-Za-z0-9_]+)\s*=\s*(?P<value>0x[0-9A-Fa-f]+|\d+)\s*;",
        text,
    ):
        constants[match.group("name")] = int(match.group("value"), 0)

    def parse_fields(array_name: str) -> tuple[FieldSpec, ...]:
        array_match = re.search(
            rf"constexpr\s+std::array<ChatFieldSpec,\s*\d+>\s+{array_name}\{{\{{(?P<body>.*?)\}}\}};",
            text,
            re.S,
        )
        if not array_match:
            raise ValueError(f"could not find {array_name} in {path}")
        fields: list[FieldSpec] = []
        for match in re.finditer(
            r"\{\s*ChatField::(?P<field>\w+)\s*,\s*(?P<name_const>k\w+NameIndex)\s*,\s*"
            r"(?P<offset>0x[0-9A-Fa-f]+|\d+)\s*,\s*(?P<size>k\w+|\d+|0x[0-9A-Fa-f]+)\s*\}",
            array_match.group("body"),
        ):
            fields.append(
                FieldSpec(
                    field=match.group("field"),
                    property_name=match.group("field"),
                    name_index_constant=match.group("name_const"),
                    offset=int(match.group("offset"), 0),
                    size_constant=match.group("size"),
                )
            )
        return tuple(fields)

    function_specs: dict[str, FunctionSpec] = {}
    field_arrays = {
        "ServerChat": parse_fields("kServerChatFields"),
        "ServerChatTo": parse_fields("kServerChatToFields"),
        "ServerChatToPlayer": parse_fields("kServerChatToPlayerFields"),
    }

    for function in DEFAULT_TARGETS:
        spec_match = re.search(
            rf"constexpr\s+ChatFunctionSpec\s+k{function}Spec\{{(?P<body>.*?)\}};",
            text,
            re.S,
        )
        if not spec_match:
            raise ValueError(f"could not find k{function}Spec in {path}")
        tokens = [
            token.strip().rstrip(",")
            for token in spec_match.group("body").splitlines()
            if token.strip() and not token.strip().startswith("ChatFunction::")
        ]
        if len(tokens) < 5:
            raise ValueError(f"k{function}Spec has unexpected initializer shape")
        function_specs[function] = FunctionSpec(
            function=function,
            name_index_constant=tokens[0],
            num_parms=int(tokens[1], 0),
            parms_size=int(tokens[2], 0),
            fields=field_arrays[function],
        )

    required = {
        "kStrPropertyClassNameIndex",
        "kStrPropertyClassObjectIndex",
        "kFStringHeaderSize",
    }
    missing = sorted(required - constants.keys())
    if missing:
        raise ValueError(f"missing ChatReflection constants: {', '.join(missing)}")

    return ChatReflectionSpec(constants=constants, functions=function_specs)


def _candidate_function_indices(
    memory: uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    max_object_scan: int,
    targets: Iterable[str],
) -> dict[str, int]:
    _metadata, objects = uobjects.iter_uobjects(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_objects=max_object_scan,
        class_contains="Function",
    )
    wanted = set(targets)
    result: dict[str, int] = {}
    for item in objects:
        name = item.get("name")
        index = item.get("index")
        if name in wanted and isinstance(index, int):
            result.setdefault(str(name), index)
    return result


def _field_size(spec: ChatReflectionSpec, field: FieldSpec) -> int:
    return _parse_cpp_int(field.size_constant, spec.constants)


def _add_check(checks: list[dict[str, object]], ok: bool, label: str, expected: object, observed: object) -> None:
    checks.append(
        {
            "status": "ok" if ok else "mismatch",
            "label": label,
            "expected": expected,
            "observed": observed,
        }
    )


def _parse_hex_address(value: object) -> int | None:
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    return int(value, 16)


def verify_core(
    memory: uobjects.CoreMemory,
    *,
    chat_spec: ChatReflectionSpec,
    gobjects: int,
    fname_root_slot: int,
    max_object_scan: int,
    window_size: int,
) -> dict[str, object]:
    indices = _candidate_function_indices(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_object_scan=max_object_scan,
        targets=DEFAULT_TARGETS,
    )
    inspector_payload = inspector.inspect_core(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        object_addresses=[],
        indices=[indices[name] for name in DEFAULT_TARGETS if name in indices],
        window_size=window_size,
        max_object_scan=max_object_scan,
    )
    targets_by_name = {
        target.get("object_summary", {}).get("name"): target
        for target in inspector_payload.get("targets", [])
        if isinstance(target.get("object_summary"), dict)
    }

    fname_table = memory.read_ptr(fname_root_slot)
    function_results: list[dict[str, object]] = []
    all_checks: list[dict[str, object]] = []

    for function_name in DEFAULT_TARGETS:
        expected = chat_spec.functions[function_name]
        target = targets_by_name.get(function_name)
        checks: list[dict[str, object]] = []
        if target is None:
            _add_check(checks, False, "core function object found", "present", "missing")
            function_results.append({"function": function_name, "status": "mismatch", "checks": checks})
            all_checks.extend(checks)
            continue

        summary = target.get("object_summary") or {}
        chain = target.get("property_chain") or {}
        properties = chain.get("properties") or []
        expected_name_index = chat_spec.constants[expected.name_index_constant]
        observed_name_index = summary.get("name_index")
        _add_check(checks, observed_name_index == expected_name_index, "FName index", expected_name_index, observed_name_index)
        _add_check(checks, chain.get("expected_count") == expected.num_parms, "NumParms", expected.num_parms, chain.get("expected_count"))
        _add_check(checks, chain.get("parms_size") == expected.parms_size, "ParmsSize", expected.parms_size, chain.get("parms_size"))
        _add_check(checks, len(properties) == len(expected.fields), "property count", len(expected.fields), len(properties))
        _add_check(checks, chain.get("status") == "candidate", "property chain status", "candidate", chain.get("status"))

        for index, field in enumerate(expected.fields):
            prefix = f"{field.property_name}[{index}]"
            prop = properties[index] if index < len(properties) and isinstance(properties[index], dict) else None
            if prop is None:
                _add_check(checks, False, f"{prefix} present", "present", "missing")
                continue
            prop_summary = prop.get("summary") if isinstance(prop.get("summary"), dict) else {}
            expected_prop_name_index = chat_spec.constants[field.name_index_constant]
            _add_check(
                checks,
                prop_summary.get("name_index") == expected_prop_name_index,
                f"{prefix} property FName index",
                expected_prop_name_index,
                prop_summary.get("name_index"),
            )
            _add_check(
                checks,
                prop_summary.get("class_name") == "StrProperty",
                f"{prefix} property class",
                "StrProperty",
                prop_summary.get("class_name"),
            )
            _add_check(checks, prop.get("offset_internal") == field.offset, f"{prefix} offset", field.offset, prop.get("offset_internal"))
            _add_check(checks, prop.get("element_size") == _field_size(chat_spec, field), f"{prefix} element size", _field_size(chat_spec, field), prop.get("element_size"))

            class_address = _parse_hex_address(prop_summary.get("class"))
            class_summary = uobjects.read_uobject(memory, class_address, fname_table) if class_address else None
            _add_check(
                checks,
                bool(class_summary) and class_summary.get("name_index") == chat_spec.constants["kStrPropertyClassNameIndex"],
                f"{prefix} StrProperty class FName index",
                chat_spec.constants["kStrPropertyClassNameIndex"],
                class_summary.get("name_index") if class_summary else None,
            )
            _add_check(
                checks,
                bool(class_summary) and class_summary.get("internal_index") == chat_spec.constants["kStrPropertyClassObjectIndex"],
                f"{prefix} StrProperty class object index",
                chat_spec.constants["kStrPropertyClassObjectIndex"],
                class_summary.get("internal_index") if class_summary else None,
            )

        status = "ok" if all(check["status"] == "ok" for check in checks) else "mismatch"
        function_results.append(
            {
                "function": function_name,
                "gobjects_index": indices.get(function_name),
                "object": target.get("object"),
                "status": status,
                "checks": checks,
            }
        )
        all_checks.extend(checks)

    return {
        "interpretation": {
            "status": "offline-verification",
            "note": "Compares local ChatReflection constexpr values to UFunction/property-chain evidence from an ELF core.",
        },
        "metadata": {
            "gobjects": f"0x{gobjects:x}",
            "fname_root_slot": f"0x{fname_root_slot:x}",
            "max_object_scan": max_object_scan,
            "window_size": f"0x{window_size:x}",
        },
        "status": "ok" if all(check["status"] == "ok" for check in all_checks) else "mismatch",
        "functions": function_results,
    }


def format_text(payload: dict[str, object]) -> str:
    lines = [
        "status={status} interpretation={interpretation}".format(
            status=payload["status"],
            interpretation=payload["interpretation"]["status"],
        )
    ]
    for function in payload["functions"]:
        lines.append(
            "function={function} index={gobjects_index} object={object} status={status}".format(**function)
        )
        for check in function["checks"]:
            lines.append(
                "  {status} {label}: expected={expected!r} observed={observed!r}".format(**check)
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify ue/ChatReflection.cpp constants against offline core chat UFunction evidence."
    )
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing ELF core dump.")
    parser.add_argument("--chat-reflection-source", type=Path, default=CHAT_REFLECTION_SOURCE)
    parser.add_argument("--gobjects", type=parse_int, default=uobjects.DEFAULT_GOBJECTS)
    parser.add_argument("--fname-root-slot", type=parse_int, default=uobjects.DEFAULT_FNAME_ROOT_SLOT)
    parser.add_argument("--max-object-scan", type=int, default=inspector.DEFAULT_MAX_OBJECT_SCAN)
    parser.add_argument("--window-size", type=parse_int, default=inspector.DEFAULT_WINDOW_SIZE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_object_scan < 0:
        raise SystemExit("--max-object-scan must be non-negative")
    if args.window_size <= 0:
        raise SystemExit("--window-size must be positive")

    chat_spec = parse_chat_reflection_source(args.chat_reflection_source)
    memory = uobjects.CoreMemory(args.core)
    try:
        payload = verify_core(
            memory,
            chat_spec=chat_spec,
            gobjects=args.gobjects,
            fname_root_slot=args.fname_root_slot,
            max_object_scan=args.max_object_scan,
            window_size=args.window_size,
        )
    finally:
        memory.close()

    payload = {"core": str(args.core), "chat_reflection_source": str(args.chat_reflection_source), **payload}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
