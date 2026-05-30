#!/usr/bin/env python3
"""Send a guarded Obelisk Discord embed through local operator webhooks."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / "local" / "discord-webhooks.env"

CHANNELS = {
    "community": {
        "env": "OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL",
        "color": 0x2ECC71,
        "purpose": "major public modder-facing milestones only",
    },
    "beta-test": {
        "env": "OBELISK_BETA_TEST_WEBHOOK_URL",
        "color": 0x3498DB,
        "purpose": "operator-approved in-game test windows only",
    },
}

RESERVED_FIELD_NAMES = frozenset({"estado", "alcance"})

FORBIDDEN_TEXT = (
    "discord.com/" + "api/webhooks",
    "discordapp.com/" + "api/webhooks",
    "raw log",
    "player text",
    "token",
    "secret",
)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def split_field(raw: str) -> dict[str, Any]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("fields must use Name=Value")
    name, value = raw.split("=", 1)
    name = name.strip()
    value = value.strip()
    if not name or not value:
        raise argparse.ArgumentTypeError("field name and value must be non-empty")
    return {"name": name[:256], "value": value[:1024], "inline": False}


def reject_forbidden_text(parts: list[str]) -> None:
    joined = "\n".join(parts).lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in joined:
            raise SystemExit(f"refusing embed text containing forbidden phrase: {forbidden}")


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    reject_forbidden_text(
        [args.title, args.description, args.status, args.scope]
        + [f"{field['name']}={field['value']}" for field in args.field]
    )
    if not (2 <= len(args.field) <= 5):
        raise SystemExit("use 2-5 embed fields to keep Discord updates concise")
    for field in args.field:
        if field["name"].casefold() in RESERVED_FIELD_NAMES:
            raise SystemExit("custom embed fields must not reuse reserved names: Estado, Alcance")

    channel = CHANNELS[args.channel]
    fields = [
        {"name": "Estado", "value": args.status[:1024], "inline": True},
        {"name": "Alcance", "value": args.scope[:1024], "inline": True},
        *args.field,
    ]

    return {
        "content": args.content,
        "embeds": [
            {
                "title": args.title[:256],
                "description": args.description[:4096],
                "color": args.color if args.color is not None else channel["color"],
                "fields": fields[:7],
                "footer": {"text": f"Obelisk | {channel['purpose']}"},
                "timestamp": args.timestamp or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        ],
    }


def load_webhook_url(args: argparse.Namespace) -> str:
    env_values = parse_env_file(args.env_file)
    env_name = CHANNELS[args.channel]["env"]
    webhook_url = os.environ.get(env_name) or env_values.get(env_name)
    if not webhook_url:
        raise SystemExit(f"missing {env_name} in environment or {args.env_file}")
    return webhook_url


def send_payload(webhook_url: str, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ObeliskDiscordGuard/1"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise SystemExit(f"discord webhook returned HTTP {response.status}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=sorted(CHANNELS), required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--field", action="append", default=[], type=split_field)
    parser.add_argument("--content", default="")
    parser.add_argument("--timestamp")
    parser.add_argument("--color", type=lambda value: int(value, 0))
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = build_payload(args)

    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    webhook_url = load_webhook_url(args)
    send_payload(webhook_url, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
