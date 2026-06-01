#!/usr/bin/env python3
"""Read-only operator CLI for Obelisk installs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("/servidor/ark/obelisk")
REQUIRED_DIRS = ("lib", "plugins", "config", "logs", "state/instances")
STABLE_INSTANCE_MARKERS = frozenset(("enable-process-event-hook", "disable-plugins"))
FORBIDDEN_STABLE_MARKERS = frozenset(
    (
        "allow-ptrace",
        "allow-observer-debug-window",
        "allow-experimental-observers",
        "enable-debug-control",
        "enable-native-exec-probes",
        "allow-global-process-event-callbacks",
        "allow-filtered-process-event-callbacks",
        "allow-call-process-event",
        "allow-process-event-blocking",
        "enable-chat-events",
        "enable-chat-reflection",
        "enable-chat-route-observer",
        "enable-inventory-reflection",
        "enable-structure-reflection",
        "enable-item-return-events",
        "enable-player-principal-lifecycle-observer",
        "enable-reflection-scanner",
        "request-static-fname-probe",
    )
)
SAFE_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def safe_json_load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc.msg}"
    except OSError as exc:
        return None, f"unreadable: {exc}"

    if not isinstance(payload, dict):
        return None, "config root is not an object"
    return payload, None


def bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "missing"


def list_text(value: Any) -> str:
    if not isinstance(value, list):
        return "missing"
    if not value:
        return "[]"
    return ",".join(str(item) for item in value)


def is_safe_instance_id(value: str) -> bool:
    return bool(SAFE_INSTANCE_ID_RE.fullmatch(value))


def validate_plugin_config_payload(payload: dict[str, Any]) -> str | None:
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return "enabled-not-boolean"

    allow_all = payload.get("allow_all_instances")
    if allow_all is not None and not isinstance(allow_all, bool):
        return "allow_all_instances-not-boolean"

    allowlist = payload.get("instance_allowlist")
    if allowlist is not None:
        if not isinstance(allowlist, list):
            return "instance_allowlist-not-array"
        for entry in allowlist:
            if not isinstance(entry, str):
                return "instance_allowlist-entry-not-string"
            if not is_safe_instance_id(entry):
                return "instance_allowlist-entry-unsafe"

    if enabled:
        if allow_all is True:
            return None
        if not isinstance(allowlist, list) or not allowlist:
            return "enabled-without-instance-scope"

    return None


def iter_regular_so(plugin_dir: Path) -> list[Path]:
    if plugin_dir.is_symlink() or not plugin_dir.is_dir():
        return []
    return sorted(
        path
        for path in plugin_dir.iterdir()
        if path.suffix == ".so" and path.is_file() and not path.is_symlink()
    )


def iter_instances(state_root: Path) -> list[Path]:
    instances_root = state_root / "instances"
    if not instances_root.is_dir():
        return []
    return sorted(
        path
        for path in instances_root.iterdir()
        if path.is_dir() and not path.is_symlink() and is_safe_instance_id(path.name)
    )


def iter_instance_entries(state_root: Path) -> list[Path]:
    instances_root = state_root / "instances"
    if not instances_root.is_dir():
        return []
    return sorted(path for path in instances_root.iterdir() if path.is_dir() or path.is_symlink())


def iter_plugin_config_entries(config_root: Path) -> list[Path]:
    if not config_root.is_dir():
        return []
    return sorted(path for path in config_root.iterdir() if path.is_dir() or path.is_symlink())


def marker_is_regular_file(instance_dir: Path, marker: str) -> bool:
    path = instance_dir / marker
    return path.is_file() and not path.is_symlink()


def marker_entry_exists(instance_dir: Path, marker: str) -> bool:
    path = instance_dir / marker
    return path.exists() or path.is_symlink()


def instance_posture_summary(instance_dir: Path) -> tuple[str, str]:
    missing_stable = sorted(
        marker for marker in STABLE_INSTANCE_MARKERS if not marker_is_regular_file(instance_dir, marker)
    )
    forbidden = sorted(marker for marker in FORBIDDEN_STABLE_MARKERS if marker_entry_exists(instance_dir, marker))

    if forbidden and missing_stable:
        posture = "experimental+incomplete"
    elif forbidden:
        posture = "experimental"
    elif missing_stable:
        posture = "incomplete"
    else:
        posture = "stable"

    details: list[str] = []
    if missing_stable:
        details.append(f"missing={','.join(missing_stable)}")
    if forbidden:
        details.append(f"forbidden={','.join(forbidden)}")
    return posture, ";".join(details) if details else "ok"


def print_table(rows: list[list[str]], headers: list[str]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def render(row: list[str]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    print(render(headers))
    print(render(["-" * width for width in widths]))
    for row in rows:
        print(render(row))


def command_status(root: Path) -> int:
    print(f"root: {root}")
    for relative in REQUIRED_DIRS:
        path = root / relative
        if path.is_symlink():
            state = "symlink"
        elif path.exists():
            state = "ok" if path.is_dir() else "not-directory"
        else:
            state = "missing"
        print(f"{relative}: {state}")

    plugins = iter_regular_so(root / "plugins")
    plugin_config_entries = iter_plugin_config_entries(root / "config")
    valid_plugin_config_entries = [
        path for path in plugin_config_entries if path.is_dir() and not path.is_symlink()
    ]
    instances = iter_instances(root / "state")
    instance_entries = iter_instance_entries(root / "state")
    print(f"plugins: {len(plugins)}")
    print(f"plugin_configs: {len(valid_plugin_config_entries)}")
    print(f"invalid_plugin_config_entries: {len(plugin_config_entries) - len(valid_plugin_config_entries)}")
    print(f"instances: {len(instances)}")
    print(f"invalid_instance_entries: {len(instance_entries) - len(instances)}")
    return 0


def command_instances_list(root: Path) -> int:
    rows: list[list[str]] = []
    for instance_dir in iter_instance_entries(root / "state"):
        if instance_dir.is_symlink():
            markers: list[str] = []
            posture = "invalid"
            details = "instance-dir-symlink"
        elif not is_safe_instance_id(instance_dir.name):
            markers = []
            posture = "invalid"
            details = "instance-id-unsafe"
        else:
            markers = sorted(
                marker.name
                for marker in instance_dir.iterdir()
                if marker.is_file() and not marker.is_symlink()
            )
            posture, details = instance_posture_summary(instance_dir)
        rows.append([instance_dir.name, posture, ",".join(markers) if markers else "[]", details])

    if not rows:
        print("No instances found.")
        return 0

    print_table(rows, ["instance", "persistent_posture", "markers", "details"])
    return 0


def plugin_config_summary(root: Path, plugin_id: str) -> tuple[str, str, str, str]:
    config_dir = root / "config" / plugin_id
    if config_dir.is_symlink():
        return ("unknown", "unknown", "unknown", "config-dir-symlink")
    if config_dir.exists() and not config_dir.is_dir():
        return ("unknown", "unknown", "unknown", "config-dir-not-directory")
    config_path = config_dir / "config.json"
    if config_path.is_symlink():
        return ("unknown", "unknown", "unknown", "config-file-symlink")
    if config_path.exists() and not config_path.is_file():
        return ("unknown", "unknown", "unknown", "config-file-not-regular")
    payload, error = safe_json_load(config_path)
    if error:
        return ("unknown", "unknown", "unknown", error)
    assert payload is not None
    validation_error = validate_plugin_config_payload(payload)
    if validation_error:
        return ("unknown", "unknown", "unknown", validation_error)
    return (
        bool_text(payload.get("enabled")),
        bool_text(payload.get("allow_all_instances")),
        list_text(payload.get("instance_allowlist")),
        "ok",
    )


def command_plugins_list(root: Path) -> int:
    plugin_files = iter_regular_so(root / "plugins")
    config_entries = iter_plugin_config_entries(root / "config")

    names = sorted({path.stem for path in plugin_files} | {path.name for path in config_entries})
    rows: list[list[str]] = []
    for name in names:
        so_path = root / "plugins" / f"{name}.so"
        enabled, allow_all, allowlist, config_state = plugin_config_summary(root, name)
        rows.append([
            name,
            "yes" if so_path.is_file() and not so_path.is_symlink() else "no",
            enabled,
            allow_all,
            allowlist,
            config_state,
        ])

    if not rows:
        print("No plugins or plugin configs found.")
        return 0

    print_table(rows, ["plugin", "published", "enabled", "all", "instances", "config"])
    return 0


def command_plugins_show(root: Path, plugin: str) -> int:
    so_path = root / "plugins" / f"{plugin}.so"
    config_dir = root / "config" / plugin
    config_path = config_dir / "config.json"
    print(f"plugin: {plugin}")
    print(f"published_so: {so_path if so_path.is_file() and not so_path.is_symlink() else 'missing'}")
    print(f"config: {config_path}")

    if config_dir.is_symlink():
        print("config_state: config-dir-symlink")
        return 1
    if config_dir.exists() and not config_dir.is_dir():
        print("config_state: config-dir-not-directory")
        return 1
    if config_path.is_symlink():
        print("config_state: config-file-symlink")
        return 1
    if config_path.exists() and not config_path.is_file():
        print("config_state: config-file-not-regular")
        return 1

    payload, error = safe_json_load(config_path)
    if error:
        print(f"config_state: {error}")
        return 1 if error != "missing" else 0

    assert payload is not None
    validation_error = validate_plugin_config_payload(payload)
    if validation_error:
        print(f"config_state: {validation_error}")
        return 1

    print("config_state: ok")
    print(f"enabled: {bool_text(payload.get('enabled'))}")
    print(f"allow_all_instances: {bool_text(payload.get('allow_all_instances'))}")
    print(f"instance_allowlist: {list_text(payload.get('instance_allowlist'))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Obelisk operator CLI.",
        epilog=(
            "Current commands only inspect install, plugin, and per-instance marker state. "
            "Lifecycle commands such as start, stop, restart, and plugin restart are "
            "post-stable and are not implemented."
        ),
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("OBELISK_ROOT", str(DEFAULT_ROOT)),
        help="Obelisk install root. Defaults to OBELISK_ROOT or /servidor/ark/obelisk.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show install root, directory, plugin, and instance summary.")

    instances = subparsers.add_parser("instances", help="Inspect instance marker state.")
    instance_subcommands = instances.add_subparsers(dest="instances_command", required=True)
    instance_subcommands.add_parser("list", help="List known instance marker directories.")

    plugins = subparsers.add_parser("plugins", help="Inspect plugin publication/config state.")
    plugin_subcommands = plugins.add_subparsers(dest="plugins_command", required=True)
    plugin_subcommands.add_parser("list", help="List published plugins and plugin configs.")
    plugin_show = plugin_subcommands.add_parser("show", help="Show one plugin config summary.")
    plugin_show.add_argument("plugin", help="Plugin id / config directory name.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.command == "status":
        return command_status(root)
    if args.command == "instances" and args.instances_command == "list":
        return command_instances_list(root)
    if args.command == "plugins" and args.plugins_command == "list":
        return command_plugins_list(root)
    if args.command == "plugins" and args.plugins_command == "show":
        return command_plugins_show(root, args.plugin)

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
