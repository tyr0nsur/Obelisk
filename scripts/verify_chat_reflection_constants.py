#!/usr/bin/env python3
"""Verify ChatReflection constants against offline core UFunction evidence.

This tool is offline-only: it reads an existing ELF core and local source files. It never
attaches to a running ARK process and never mutates server state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
import inspect_core_ufunctions as inspector  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path  # noqa: E402


CHAT_REFLECTION_SOURCE = REPO_ROOT / "ue" / "ChatReflection.cpp"
DEFAULT_SERVER_SEND_CHAT_NATIVE_EXEC = 0x154A600
EXPECTED_SEND_MODE_NAMES = (
    "EChatSendMode::GlobalChat",
    "EChatSendMode::GlobalTribeChat",
    "EChatSendMode::LocalChat",
    "EChatSendMode::AllianceChat",
    "EChatSendMode::MAX",
    "EChatSendMode::EChatSendMode_MAX",
)
DEFAULT_TARGETS = (
    "ServerChat",
    "ServerChatTo",
    "ServerChatToPlayer",
    "ServerSendChatMessage",
    "ClientChatMessage",
    "ClientServerChatDirectMessage",
    "ClientServerChatMessage",
    "SendServerChatMessage",
    "OnServerChatMessageDelegate",
)

CORE_FUNCTION_NAMES = {
    "OnServerChatMessageDelegate": "OnServerChatMessage__DelegateSignature",
}


@dataclass(frozen=True)
class FieldSpec:
    field: str
    property_name: str
    name_index_constant: str
    offset: int
    size_constant: str
    class_name_index_constant: str
    class_object_index_constant: str


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


@dataclass(frozen=True)
class EvidencePack:
    manifest_path: Path
    manifest: dict[str, object]
    core: Path
    core_sha256: str | None
    gobjects: int
    fname_root_slot: int
    binary_sha256: str | None


def parse_int(value: str) -> int:
    return int(value, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(path: Path) -> Path:
    return path / "manifest.json" if path.is_dir() else path


def _evidence_pack_manifest_path(path: Path) -> Path:
    reject_protected_input_path(path, "--evidence-pack")
    manifest_path = _manifest_path(path)
    reject_protected_input_path(manifest_path, "--evidence-pack")
    return manifest_path


def _first_address(manifest: dict[str, object], key: str) -> int:
    values = manifest.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"evidence pack manifest missing non-empty {key}")
    first = values[0]
    if not isinstance(first, dict) or not isinstance(first.get("address"), str):
        raise ValueError(f"evidence pack manifest has invalid {key}[0].address")
    return int(str(first["address"]), 0)


def load_evidence_pack(
    path: Path,
    *,
    verify_binary_sha: bool = True,
    verify_core_sha: bool = True,
) -> EvidencePack:
    manifest_path = _evidence_pack_manifest_path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("evidence pack manifest must be a JSON object")

    core_payload = manifest.get("core")
    if not isinstance(core_payload, dict) or not isinstance(core_payload.get("path"), str):
        raise ValueError("evidence pack manifest missing core.path")
    core = Path(str(core_payload["path"]))
    reject_protected_input_path(core, f"{manifest_path}: evidence pack core.path")
    if not core.is_file():
        raise ValueError(f"evidence pack core does not exist: {core}")
    core_sha256 = core_payload.get("sha256")
    if not isinstance(core_sha256, str) or not core_sha256:
        core_sha256 = None
    if verify_core_sha and core_sha256:
        observed_core_sha = sha256_file(core)
        if observed_core_sha != core_sha256:
            raise ValueError(
                "evidence pack core sha256 mismatch: "
                f"expected {core_sha256} observed {observed_core_sha}"
            )

    binary_sha256: str | None = None
    binary_payload = manifest.get("binary")
    if isinstance(binary_payload, dict):
        binary_sha = binary_payload.get("sha256")
        if isinstance(binary_sha, str) and binary_sha:
            binary_sha256 = binary_sha
        binary_path_value = binary_payload.get("path")
        binary_path = None
        if isinstance(binary_path_value, str):
            binary_path = Path(binary_path_value)
            reject_protected_input_path(binary_path, f"{manifest_path}: evidence pack binary.path")
        if verify_binary_sha and binary_sha256 and binary_path is not None:
            if not binary_path.is_file():
                raise ValueError(f"evidence pack binary does not exist: {binary_path}")
            observed_sha = sha256_file(binary_path)
            if observed_sha != binary_sha256:
                raise ValueError(
                    "evidence pack binary sha256 mismatch: "
                    f"expected {binary_sha256} observed {observed_sha}"
                )

    return EvidencePack(
        manifest_path=manifest_path,
        manifest=manifest,
        core=core,
        core_sha256=core_sha256,
        gobjects=_first_address(manifest, "gobjects_candidates"),
        fname_root_slot=_first_address(manifest, "fname_root_slots"),
        binary_sha256=binary_sha256,
    )


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
        r"(?P<name>k[A-Za-z0-9_]+)\s*=\s*(?P<value>0x[0-9A-Fa-f]+|-?\d+)\s*;",
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
        field_pattern = re.compile(
            r"\{\s*ChatField::(?P<field>\w+)\s*,\s*(?P<name_const>k\w+NameIndex)\s*,\s*"
            r"(?P<offset>0x[0-9A-Fa-f]+|\d+)\s*,\s*(?P<size>k\w+|\d+|0x[0-9A-Fa-f]+)"
            r"(?:\s*,\s*(?P<class_name_const>k\w+ClassNameIndex)\s*,\s*"
            r"(?P<class_object_const>k\w+ObjectIndex))?\s*\}",
            re.S,
        )
        for match in field_pattern.finditer(array_match.group("body")):
            fields.append(
                FieldSpec(
                    field=match.group("field"),
                    property_name=match.group("field"),
                    name_index_constant=match.group("name_const"),
                    offset=int(match.group("offset"), 0),
                    size_constant=match.group("size"),
                    class_name_index_constant=match.group("class_name_const") or "kStrPropertyClassNameIndex",
                    class_object_index_constant=match.group("class_object_const")
                    or "kStrPropertyClassObjectIndex",
                )
            )
        return tuple(fields)

    function_specs: dict[str, FunctionSpec] = {}
    field_arrays = {
        "ServerChat": parse_fields("kServerChatFields"),
        "ServerChatTo": parse_fields("kServerChatToFields"),
        "ServerChatToPlayer": parse_fields("kServerChatToPlayerFields"),
        "ServerSendChatMessage": parse_fields("kServerSendChatMessageFields"),
        "ClientChatMessage": parse_fields("kClientChatMessageFields"),
        "ClientServerChatDirectMessage": parse_fields("kClientServerChatMessageFields"),
        "ClientServerChatMessage": parse_fields("kClientServerChatMessageFields"),
        "SendServerChatMessage": parse_fields("kSendServerChatMessageFields"),
        "OnServerChatMessageDelegate": parse_fields("kOnServerChatMessageDelegateFields"),
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
        "kAnyNameIndex",
        "kAnyObjectIndex",
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
    wanted = {CORE_FUNCTION_NAMES.get(target, target): target for target in targets}
    result: dict[str, int] = {}
    for item in objects:
        name = item.get("name")
        index = item.get("index")
        if name in wanted and isinstance(index, int):
            result.setdefault(wanted[str(name)], index)
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


def _read_i32(memory: uobjects.CoreMemory, address: int) -> int | None:
    data = memory.read(address, 4)
    return None if data is None else struct.unpack("<i", data)[0]


def _read_send_mode_enum(memory: uobjects.CoreMemory, fname_table: int | None, property_address: int) -> dict[str, object]:
    enum_address = memory.read_ptr(property_address + 0x70)
    names_address = memory.read_ptr(enum_address + 0x40) if enum_address else None
    count = _read_i32(memory, enum_address + 0x48) if enum_address else None
    names: list[str | None] = []
    if names_address and count is not None and 0 <= count <= 32:
        for index in range(count):
            raw = memory.read(names_address + index * 8, 8)
            if raw is None:
                names.append(None)
                continue
            name_index, name_number = struct.unpack("<ii", raw)
            names.append(uobjects.resolve_fname(memory, fname_table, name_index, name_number).text)

    return {
        "enum": f"0x{enum_address:x}" if enum_address else None,
        "names": f"0x{names_address:x}" if names_address else None,
        "count": count,
        "values": names,
    }


def verify_core(
    memory: uobjects.CoreMemory,
    *,
    chat_spec: ChatReflectionSpec,
    gobjects: int,
    fname_root_slot: int,
    max_object_scan: int,
    window_size: int,
    expected_server_send_chat_native: int | None,
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
        CORE_FUNCTION_NAMES.get(function_name, function_name): target
        for function_name in DEFAULT_TARGETS
        for target in inspector_payload.get("targets", [])
        if isinstance(target.get("object_summary"), dict)
        and target.get("object_summary", {}).get("name") == CORE_FUNCTION_NAMES.get(function_name, function_name)
    }
    targets_by_function = {
        function_name: targets_by_name.get(CORE_FUNCTION_NAMES.get(function_name, function_name))
        for function_name in DEFAULT_TARGETS
    }
    targets_by_name = {
        function_name: target
        for function_name, target in targets_by_function.items()
        if target is not None
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
        _add_check(
            checks,
            target.get("object_membership_status") == "candidate-uobject",
            "object membership",
            "candidate-uobject",
            target.get("object_membership_status"),
        )
        _add_check(
            checks,
            target.get("class_membership_status") == "candidate-uobject",
            "class membership",
            "candidate-uobject",
            target.get("class_membership_status"),
        )
        _add_check(
            checks,
            target.get("outer_membership_status") == "candidate-uobject",
            "outer membership",
            "candidate-uobject",
            target.get("outer_membership_status"),
        )
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
            _add_check(
                checks,
                prop.get("membership_status") == "candidate-uobject",
                f"{prefix} membership",
                "candidate-uobject",
                prop.get("membership_status"),
            )
            _add_check(
                checks,
                prop.get("class_membership_status") == "candidate-uobject",
                f"{prefix} class membership",
                "candidate-uobject",
                prop.get("class_membership_status"),
            )
            _add_check(
                checks,
                prop.get("outer_membership_status") == "candidate-uobject",
                f"{prefix} outer membership",
                "candidate-uobject",
                prop.get("outer_membership_status"),
            )
            expected_prop_name_index = chat_spec.constants[field.name_index_constant]
            expected_class_name_index = chat_spec.constants[field.class_name_index_constant]
            expected_class_object_index = chat_spec.constants[field.class_object_index_constant]
            expected_class_name = (
                uobjects.resolve_fname(memory, fname_table, expected_class_name_index).text
                or expected_class_name_index
            )
            if expected_prop_name_index == chat_spec.constants["kAnyNameIndex"]:
                _add_check(
                    checks,
                    True,
                    f"{prefix} property FName index",
                    "any",
                    prop_summary.get("name_index"),
                )
            else:
                _add_check(
                    checks,
                    prop_summary.get("name_index") == expected_prop_name_index,
                    f"{prefix} property FName index",
                    expected_prop_name_index,
                    prop_summary.get("name_index"),
                )
            _add_check(
                checks,
                prop_summary.get("class_name") == expected_class_name,
                f"{prefix} property class",
                expected_class_name,
                prop_summary.get("class_name"),
            )
            _add_check(checks, prop.get("offset_internal") == field.offset, f"{prefix} offset", field.offset, prop.get("offset_internal"))
            _add_check(checks, prop.get("element_size") == _field_size(chat_spec, field), f"{prefix} element size", _field_size(chat_spec, field), prop.get("element_size"))

            class_address = _parse_hex_address(prop_summary.get("class"))
            class_summary = uobjects.read_uobject(memory, class_address, fname_table) if class_address else None
            _add_check(
                checks,
                bool(class_summary) and class_summary.get("name_index") == expected_class_name_index,
                f"{prefix} property class FName index",
                expected_class_name_index,
                class_summary.get("name_index") if class_summary else None,
            )
            if expected_class_object_index == chat_spec.constants["kAnyObjectIndex"]:
                _add_check(
                    checks,
                    bool(class_summary),
                    f"{prefix} property class object index",
                    "any",
                    class_summary.get("internal_index") if class_summary else None,
                )
            else:
                _add_check(
                    checks,
                    bool(class_summary) and class_summary.get("internal_index") == expected_class_object_index,
                    f"{prefix} property class object index",
                    expected_class_object_index,
                    class_summary.get("internal_index") if class_summary else None,
                )

        if function_name == "ServerSendChatMessage":
            function_address = _parse_hex_address(target.get("object"))
            native_exec = memory.read_ptr(function_address + 0xA8) if function_address else None
            native_segment = memory.segment_for_vaddr(native_exec, 1) if native_exec else None
            _add_check(
                checks,
                native_exec == expected_server_send_chat_native,
                "native exec candidate",
                f"0x{expected_server_send_chat_native:x}" if expected_server_send_chat_native is not None else None,
                f"0x{native_exec:x}" if native_exec is not None else None,
            )
            _add_check(
                checks,
                bool(native_segment and native_segment.flags & 0x1),
                "native exec segment executable",
                True,
                bool(native_segment and native_segment.flags & 0x1),
            )

            send_mode_property = None
            for index, field in enumerate(expected.fields):
                if field.field == "SendMode" and index < len(properties) and isinstance(properties[index], dict):
                    send_mode_property = properties[index]
                    break
            send_mode_property_address = _parse_hex_address(send_mode_property.get("address")) if send_mode_property else None
            enum_payload = (
                _read_send_mode_enum(memory, fname_table, send_mode_property_address)
                if send_mode_property_address is not None
                else {"values": []}
            )
            _add_check(
                checks,
                tuple(enum_payload.get("values") or ()) == EXPECTED_SEND_MODE_NAMES,
                "SendMode enum values",
                list(EXPECTED_SEND_MODE_NAMES),
                enum_payload.get("values"),
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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--core", type=Path, help="Path to an existing ELF core dump.")
    source.add_argument(
        "--evidence-pack",
        type=Path,
        help="Path to a core evidence pack directory or manifest.json. Preferred over raw --core.",
    )
    parser.add_argument("--chat-reflection-source", type=Path, default=CHAT_REFLECTION_SOURCE)
    parser.add_argument(
        "--gobjects",
        type=parse_int,
        default=None,
        help="GUObjectArray address for legacy --core mode. In --evidence-pack mode this comes from manifest.json.",
    )
    parser.add_argument(
        "--fname-root-slot",
        type=parse_int,
        default=None,
        help="FName root slot for legacy --core mode. In --evidence-pack mode this comes from manifest.json.",
    )
    parser.add_argument("--max-object-scan", type=int, default=inspector.DEFAULT_MAX_OBJECT_SCAN)
    parser.add_argument("--window-size", type=parse_int, default=inspector.DEFAULT_WINDOW_SIZE)
    parser.add_argument(
        "--expected-server-send-chat-native",
        type=parse_int,
        default=DEFAULT_SERVER_SEND_CHAT_NATIVE_EXEC,
        help="Binary-hash-scoped native exec pointer used only as offline cross-validation evidence.",
    )
    parser.add_argument(
        "--no-verify-binary-sha",
        action="store_true",
        help="When using --evidence-pack, do not hash the manifest binary path.",
    )
    parser.add_argument(
        "--no-verify-core-sha",
        action="store_true",
        help="When using --evidence-pack, do not hash the manifest core path even if core.sha256 is present.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_object_scan < 0:
        raise SystemExit("--max-object-scan must be non-negative")
    if args.window_size <= 0:
        raise SystemExit("--window-size must be positive")

    evidence_pack: EvidencePack | None = None
    core = args.core
    gobjects = args.gobjects if args.gobjects is not None else uobjects.DEFAULT_GOBJECTS
    fname_root_slot = (
        args.fname_root_slot
        if args.fname_root_slot is not None
        else uobjects.DEFAULT_FNAME_ROOT_SLOT
    )
    if args.evidence_pack:
        if args.gobjects is not None or args.fname_root_slot is not None:
            raise SystemExit("--evidence-pack reads gobjects and fname root from manifest; do not pass overrides")
        try:
            evidence_pack = load_evidence_pack(
                args.evidence_pack,
                verify_binary_sha=not args.no_verify_binary_sha,
                verify_core_sha=not args.no_verify_core_sha,
            )
        except ValueError as error:
            raise SystemExit(str(error)) from error
        core = evidence_pack.core
        gobjects = evidence_pack.gobjects
        fname_root_slot = evidence_pack.fname_root_slot
    else:
        reject_protected_input_path(core, "--core")

    chat_spec = parse_chat_reflection_source(args.chat_reflection_source)
    memory = uobjects.CoreMemory(core)
    try:
        payload = verify_core(
            memory,
            chat_spec=chat_spec,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_object_scan=args.max_object_scan,
            window_size=args.window_size,
            expected_server_send_chat_native=args.expected_server_send_chat_native,
        )
    finally:
        memory.close()

    payload = {
        "core": str(core),
        "chat_reflection_source": str(args.chat_reflection_source),
        **payload,
    }
    if evidence_pack:
        payload["evidence_pack"] = {
            "manifest": str(evidence_pack.manifest_path),
            "binary_sha256": evidence_pack.binary_sha256,
            "core_sha256": evidence_pack.core_sha256,
        }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
