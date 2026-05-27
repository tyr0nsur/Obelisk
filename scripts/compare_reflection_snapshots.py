#!/usr/bin/env python3
"""Compare sanitized UFunction/ScriptStruct snapshot layouts from two evidence roots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import re


SUPPORTED_SCHEMAS = {
    "obelisk.ufunction-chain.snapshot.v1",
    "obelisk.scriptstruct-chain.snapshot.v1",
}
FORBIDDEN_KEYS = {
    "object",
    "address",
    "first_property",
    "next_field",
    "next_property",
    "pointer_window",
    "integer_window",
    "gobjects",
    "fname_table",
    "chunks",
    "native_func_candidate",
}
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{8,}")
HEX_METADATA_KEYS = {"property_flags", "return_value_offset", "function_flags"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two sanitized reflection snapshot roots without reading cores or touching servers."
    )
    parser.add_argument("--base-root", required=True, type=Path, help="Baseline snapshot root or single snapshot file.")
    parser.add_argument("--candidate-root", required=True, type=Path, help="Second-source snapshot root or file.")
    parser.add_argument(
        "--allow-ark-sha-mismatch",
        action="store_true",
        help="Do not mark targets inconclusive when evidence.ark_binary_sha256 differs.",
    )
    parser.add_argument(
        "--strict-identity-indices",
        action="store_true",
        help="Also require FName/object identity indices to match where snapshots carry them.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def snapshot_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        raise SystemExit(f"snapshot root does not exist: {root}")
    return sorted(path for path in root.rglob("*.snapshot.json") if path.is_file())


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if payload.get("schema") not in SUPPORTED_SCHEMAS:
        raise SystemExit(f"{path}: unsupported snapshot schema: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{path}: expected exactly one target")
    return payload


def target_key(payload: dict[str, Any]) -> str:
    target = payload["targets"][0]
    identity = target.get("target")
    if not isinstance(identity, dict):
        raise SystemExit("snapshot target missing identity object")
    schema = payload.get("schema")
    outer = identity.get("outer_name")
    name = identity.get("name")
    if not isinstance(outer, str) or not isinstance(name, str):
        raise SystemExit("snapshot target missing string outer_name/name")
    return f"{schema}:{outer}.{name}"


def load_snapshot_set(root: Path) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for path in snapshot_paths(root):
        payload = load_snapshot(path)
        key = target_key(payload)
        if key in snapshots:
            raise SystemExit(f"duplicate snapshot target {key}: {snapshots[key]['path']} and {path}")
        snapshots[key] = {"path": str(path), "payload": payload}
    return snapshots


def raw_sanitization_reasons(value: Any, *, key: str | None = None, path: str = "") -> list[str]:
    reasons: list[str] = []
    if key in FORBIDDEN_KEYS:
        reasons.append(f"forbidden_key:{path or key}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            reasons.extend(raw_sanitization_reasons(child, key=str(child_key), path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reasons.extend(raw_sanitization_reasons(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and key not in HEX_METADATA_KEYS and ADDRESS_RE.search(value):
        reasons.append(f"raw_address:{path}")
    return reasons


def property_layout(prop: dict[str, Any], *, strict_identity_indices: bool) -> dict[str, Any]:
    result = {
        "name": prop.get("name"),
        "class_name": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "property_flags": prop.get("property_flags"),
        "status": prop.get("status"),
        "reject_reasons": prop.get("reject_reasons", []),
        "membership_status": prop.get("membership_status"),
        "class_membership_status": prop.get("class_membership_status"),
        "outer_membership_status": prop.get("outer_membership_status"),
    }
    if strict_identity_indices:
        result.update(
            {
                "object_index": prop.get("object_index"),
                "name_index": prop.get("name_index"),
                "class_name_index": prop.get("class_name_index"),
                "class_object_index": prop.get("class_object_index"),
            }
        )
    for nested_key in ("array_inner_candidate", "struct_type_candidate"):
        nested = prop.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_identity_key = "inner_property" if nested_key == "array_inner_candidate" else "struct_type"
        nested_identity = nested.get(nested_identity_key)
        if not isinstance(nested_identity, dict):
            continue
        result[nested_key] = {
            "status": nested.get("status"),
            "reject_reasons": nested.get("reject_reasons", []),
            "membership_status": nested.get("membership_status"),
            nested_identity_key: {
                "name": nested_identity.get("name"),
                "class_name": nested_identity.get("class_name"),
            },
        }
        if strict_identity_indices:
            result[nested_key][nested_identity_key]["object_index"] = nested_identity.get("object_index")
            result[nested_key][nested_identity_key]["class_name_index"] = nested_identity.get("class_name_index")
            result[nested_key][nested_identity_key]["class_object_index"] = nested_identity.get("class_object_index")
    return result


def comparable_layout(payload: dict[str, Any], *, strict_identity_indices: bool) -> tuple[dict[str, Any] | None, list[str]]:
    raw_reasons = raw_sanitization_reasons(payload)
    if raw_reasons:
        return None, raw_reasons
    target = payload["targets"][0]
    identity = target.get("target")
    chain = target.get("property_chain")
    if not isinstance(identity, dict) or not isinstance(chain, dict):
        return None, ["missing_target_identity_or_property_chain"]
    if target.get("status") != "candidate":
        return None, [f"target_status_{target.get('status')}"]
    membership = target.get("membership")
    if membership != {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"}:
        return None, ["target_membership_not_candidate"]
    if chain.get("status") != "candidate":
        return None, [f"property_chain_status_{chain.get('status')}"]
    if chain.get("reject_reasons", []):
        return None, ["property_chain_has_reject_reasons"]
    properties = chain.get("properties")
    if not isinstance(properties, list):
        return None, ["missing_property_list"]

    layout = {
        "schema": payload.get("schema"),
        "inspection_mode": target.get("inspection_mode"),
        "status": target.get("status"),
        "reject_reasons": target.get("reject_reasons", []),
        "membership": membership,
        "target": {
            "name": identity.get("name"),
            "class_name": identity.get("class_name"),
            "outer_name": identity.get("outer_name"),
            "outer_class_name": identity.get("outer_class_name"),
        },
        "property_chain": {
            "status": chain.get("status"),
            "reject_reasons": chain.get("reject_reasons", []),
            "expected_count": chain.get("expected_count"),
            "observed_count": chain.get("observed_count"),
            "properties": [
                property_layout(prop, strict_identity_indices=strict_identity_indices)
                for prop in properties
                if isinstance(prop, dict)
            ],
        },
    }
    if strict_identity_indices:
        layout["target"].update(
            {
                "object_index": identity.get("object_index"),
                "name_index": identity.get("name_index"),
                "class_name_index": identity.get("class_name_index"),
                "class_object_index": identity.get("class_object_index"),
                "outer_name_index": identity.get("outer_name_index"),
                "outer_object_index": identity.get("outer_object_index"),
            }
        )
    if payload.get("schema") == "obelisk.ufunction-chain.snapshot.v1":
        layout.update(
            {
                "num_parms": target.get("num_parms"),
                "parms_size": target.get("parms_size"),
                "function_flags": target.get("function_flags"),
                "return_value_offset": target.get("return_value_offset"),
            }
        )
        layout["property_chain"]["parms_size"] = chain.get("parms_size")
    else:
        layout.update(
            {
                "properties_size": target.get("properties_size"),
                "min_alignment": target.get("min_alignment"),
            }
        )
        layout["property_chain"]["properties_size"] = chain.get("properties_size")
    if len(layout["property_chain"]["properties"]) != len(properties):
        return None, ["non_object_property_entry"]
    return layout, []


def diff_layout(base: Any, candidate: Any, path: str = "") -> list[dict[str, Any]]:
    if type(base) is not type(candidate):
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    if isinstance(base, dict):
        diffs: list[dict[str, Any]] = []
        for key in sorted(set(base) | set(candidate)):
            diffs.extend(diff_layout(base.get(key), candidate.get(key), f"{path}.{key}" if path else key))
        return diffs
    if isinstance(base, list):
        diffs = []
        if len(base) != len(candidate):
            diffs.append({"path": f"{path}.length" if path else "length", "base": len(base), "candidate": len(candidate)})
        for index, (left, right) in enumerate(zip(base, candidate)):
            diffs.extend(diff_layout(left, right, f"{path}[{index}]"))
        return diffs
    if base != candidate:
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    return []


def evidence_sha(payload: dict[str, Any]) -> Any:
    evidence = payload.get("evidence")
    return evidence.get("ark_binary_sha256") if isinstance(evidence, dict) else None


def compare_sets(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    strict_identity_indices: bool,
    allow_ark_sha_mismatch: bool,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for key in sorted(set(base) | set(candidate)):
        if key not in candidate:
            results.append({"target": key, "status": "inconclusive", "reasons": ["missing_candidate_snapshot"]})
            continue
        if key not in base:
            results.append({"target": key, "status": "inconclusive", "reasons": ["missing_base_snapshot"]})
            continue
        if not allow_ark_sha_mismatch and evidence_sha(base[key]["payload"]) != evidence_sha(candidate[key]["payload"]):
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": ["ark_binary_sha256_mismatch"],
                }
            )
            continue
        base_layout, base_reasons = comparable_layout(base[key]["payload"], strict_identity_indices=strict_identity_indices)
        candidate_layout, candidate_reasons = comparable_layout(
            candidate[key]["payload"],
            strict_identity_indices=strict_identity_indices,
        )
        if base_reasons or candidate_reasons or base_layout is None or candidate_layout is None:
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": [f"base:{reason}" for reason in base_reasons]
                    + [f"candidate:{reason}" for reason in candidate_reasons],
                }
            )
            continue
        diffs = diff_layout(base_layout, candidate_layout)
        if diffs:
            results.append({"target": key, "status": "rejected", "diffs": diffs})
        else:
            results.append({"target": key, "status": "accepted"})
    counts = {"accepted": 0, "rejected": 0, "inconclusive": 0}
    for result in results:
        counts[result["status"]] += 1
    return {
        "schema": "obelisk.reflection-snapshot-comparison.v1",
        "strict_identity_indices": strict_identity_indices,
        "allow_ark_sha_mismatch": allow_ark_sha_mismatch,
        "counts": counts,
        "results": results,
    }


def print_text(report: dict[str, Any]) -> None:
    counts = report["counts"]
    print(
        "summary accepted={accepted} rejected={rejected} inconclusive={inconclusive}".format(
            **counts,
        )
    )
    for result in report["results"]:
        line = f"{result['status']} {result['target']}"
        if result["status"] == "rejected":
            first = result.get("diffs", [{}])[0]
            line += f" first_diff={first.get('path')} base={first.get('base')!r} candidate={first.get('candidate')!r}"
        elif result["status"] == "inconclusive":
            line += " reasons=" + ",".join(result.get("reasons", []))
        print(line)


def main() -> int:
    args = parse_args()
    base = load_snapshot_set(args.base_root)
    candidate = load_snapshot_set(args.candidate_root)
    report = compare_sets(
        base,
        candidate,
        strict_identity_indices=args.strict_identity_indices,
        allow_ark_sha_mismatch=args.allow_ark_sha_mismatch,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    if report["counts"]["rejected"]:
        return 1
    if report["counts"]["inconclusive"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
