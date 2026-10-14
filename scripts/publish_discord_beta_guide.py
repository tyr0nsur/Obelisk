#!/usr/bin/env python3
"""Publish a reviewed beta guide to the operator-selected Obelisk announcements.

REST only: no gateway, tester buttons, gameplay, retries, or crossposting. A local
state file identifies the sole editable notice. Dry-run receipts bind the exact
summary, guide bytes, destination, and create/update operation. Discord API v10
upload/edit contracts: https://docs.discord.com/developers/reference#uploading-files
and https://docs.discord.com/developers/resources/message#create-message.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.request

import discord_beta_bridge as bridge
import protected_paths


CHANNEL_ID = "1511127623432933497"
GUILD_ID = "1511110561331544085"
DEFAULT_STATE = bridge.REPO_ROOT / "local/discord-beta-guide/announcements-notice.json"
STATE_SCHEMA = "obelisk.discord-beta-guide-notice.v1"
PLAN_SCHEMA = "obelisk.discord-beta-guide-plan.v1"
RECEIPT_PREFIX = "obelisk-beta-guide:"
GUIDE_MAX_BYTES = 128 * 1024
FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,91}\.md$", re.IGNORECASE)
FORBIDDEN_GUIDE_RE = re.compile(
    r"(?:https?://)?discord(?:app)?\.com/api/webhooks|webhook[_ -]?url\s*[:=]|"
    r"(?:bot[_ -]?)?token\s*[:=]|secret\s*[:=]|(?:password|contrase[nñ]a)\s*[:=]|"
    r"(?:unique[_ -]?net|steam[_ -]?id|eos[_ -]?id|ip(?:v4|v6)?)\s*[:=]\s*[^\s<]|"
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b\d{15,20}\b|\b0x[0-9a-f]{6,16}\b|"
    r"@(?:everyone|here)\b|<@(?:!|&)?\d+>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Guide:
    filename: str
    data: bytes = field(repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            "filename": self.filename,
            "byte_length": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "content_type": "text/markdown; charset=utf-8",
        }


def read_regular_file(path: Path, max_bytes: int) -> bytes:
    """Walk with directory descriptors and O_NOFOLLOW, including every ancestor."""
    path = path.expanduser().absolute()
    if ".." in path.parts:
        raise ValueError("input path must not contain parent traversal")
    protected_paths.reject_symlink_component(path, "input_file")
    protected_paths.reject_protected_input_path(path, "input_file")
    directory_fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    file_fd = None
    try:
        for part in path.parts[1:-1]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("input must be a regular file")
        if before.st_size > max_bytes:
            raise ValueError("input exceeds maximum byte length")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(file_fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        if len(data) > max_bytes:
            raise ValueError("input exceeds maximum byte length")
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ) or len(data) != after.st_size:
            raise ValueError("input changed while being read")
        return data
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def reject_private_text(text: str, config: dict[str, str]) -> None:
    # Checklist prose may mention evidence/progress; those words are not claims.
    if FORBIDDEN_GUIDE_RE.search(text) or bridge.DISCORD_TOKEN_SHAPE_RE.search(text):
        raise ValueError("guide or summary contains private data or mentions")
    sensitive = [config.get(bridge.TOKEN_ENV, ""), config.get(bridge.SALT_ENV, "")]
    sensitive.extend(
        value for key, value in os.environ.items()
        if re.search(r"(?:ARK|OBELISK).*?(?:PASSWORD|SECRET|TOKEN)$", key)
    )
    if any(value and len(value) >= 8 and value in text for value in sensitive):
        raise ValueError("guide or summary contains a configured private value")
    if any(ord(char) < 32 and char not in "\n\r\t" or 127 <= ord(char) <= 159 for char in text):
        raise ValueError("guide or summary contains control characters")


def load_guide(path: Path, config: dict[str, str]) -> Guide:
    if not FILENAME_RE.fullmatch(path.name):
        raise ValueError("guide filename must be a simple ASCII Markdown filename")
    data = read_regular_file(path, GUIDE_MAX_BYTES)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("guide must be valid UTF-8") from exc
    if not text.strip():
        raise ValueError("guide must be non-empty")
    reject_private_text(text, config)
    return Guide(path.name, data)


def load_state(path: Path) -> dict[str, object] | None:
    protected_paths.reject_symlink_component(path, "notice_state")
    protected_paths.reject_protected_input_path(path, "notice_state")
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    try:
        value = json.loads(read_regular_file(path, 16 * 1024))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("notice state is invalid") from exc
    if (
        not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA
        or value.get("guild_id") != GUILD_ID or value.get("channel_id") != CHANNEL_ID
        or not isinstance(value.get("message_id"), str)
        or not re.fullmatch(r"[0-9]{1,20}", value["message_id"])
    ):
        raise ValueError("notice state does not identify the configured destination")
    return value


def build_plan(content: str, guide: Guide, state: dict[str, object] | None) -> dict[str, object]:
    message_id = str(state["message_id"]) if state else None
    plan: dict[str, object] = {
        "schema": PLAN_SCHEMA,
        "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID,
        "http_method": "PATCH" if state else "POST",
        "message_id": message_id,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_length": len(content),
        "guide": guide.metadata(),
        "allowed_mentions": {"parse": []},
        "components": [],
        "replace_attachments_with_current_guide": True,
        "automatic_retry": False,
        "fallback_create_on_update_error": False,
        "communication_only": True,
        "counts_as_gameplay_acceptance": False,
    }
    if not state:
        seed = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
        plan["nonce"] = str(int.from_bytes(hashlib.sha256(seed).digest()[:8], "big"))
        plan["enforce_nonce"] = True
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
    plan["dry_run_receipt"] = RECEIPT_PREFIX + hashlib.sha256(canonical).hexdigest()
    return plan


def multipart_payload(content: str, guide: Guide, plan: dict[str, object]) -> tuple[bytes, str]:
    payload: dict[str, object] = {
        "content": content,
        "allowed_mentions": {"parse": []},
        "components": [],
        "attachments": [{"id": 0, "filename": guide.filename}],
    }
    if plan["http_method"] == "POST":
        payload.update(nonce=plan["nonce"], enforce_nonce=True)
    json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    while True:
        boundary = "ObeliskGuide" + os.urandom(16).hex()
        boundary_bytes = boundary.encode("ascii")
        if boundary_bytes not in guide.data and boundary_bytes not in json_bytes:
            break
    body = b"".join([
        b"--" + boundary_bytes + b'\r\nContent-Disposition: form-data; name="payload_json"\r\n',
        b"Content-Type: application/json\r\n\r\n", json_bytes, b"\r\n",
        b"--" + boundary_bytes + b'\r\nContent-Disposition: form-data; name="files[0]"; filename="',
        guide.filename.encode("ascii"), b'"\r\nContent-Type: text/markdown; charset=utf-8\r\n\r\n',
        guide.data, b"\r\n--" + boundary_bytes + b"--\r\n",
    ])
    return body, f"multipart/form-data; boundary={boundary}"


@contextmanager
def notice_lock(path: Path):
    protected_paths.reject_symlink_component(path, "notice_state")
    protected_paths.reject_protected_output_path(path, "notice_state")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = path.parent.stat()
    if directory.st_uid != os.getuid() or stat.S_IMODE(directory.st_mode) != 0o700:
        raise ValueError("notice state directory must be owned and private (0700)")
    lock_path = path.with_name(path.name + ".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError("notice lock must be an owned regular file")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def write_state(path: Path, value: dict[str, object]) -> None:
    protected_paths.reject_symlink_component(path, "notice_state")
    fd, temporary = tempfile.mkstemp(prefix=".notice-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, sort_keys=True, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_destination(config: dict[str, str]) -> None:
    """Read only the selected channel and require its independently verified guild."""
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}",
        headers={"User-Agent": "ObeliskBetaGuide/1",
                 "Authorization": "Bot " + config[bridge.TOKEN_ENV]},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if int(response.status) != 200:
                raise ValueError("Discord destination cannot be verified; publication not attempted")
            destination = json.loads(response.read(1024 * 1024))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Discord destination returned HTTP {exc.code}; publication not attempted") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Discord destination cannot be verified; publication not attempted") from None
    if (
        not isinstance(destination, dict) or destination.get("id") != CHANNEL_ID
        or destination.get("guild_id") != GUILD_ID or destination.get("type") not in (0, 5)
    ):
        raise ValueError("Discord destination does not match the selected guild and channel")


def publish_guide(
    *, guide_file: Path, content: str, env_file: Path = bridge.DEFAULT_ENV_PATH,
    state_file: Path = DEFAULT_STATE, dry_run: bool = True,
    confirmed_send: bool = False, dry_run_receipt: str | None = None,
) -> dict[str, object]:
    config = bridge.merged_config(env_file)
    # The legacy beta-channel guild in the bot env does not select this destination.
    # The operator selected this channel; the mandatory GET verifies its actual guild.
    # Both plan and send retain the exact same normalized summary.
    content = "\n".join(line.rstrip() for line in content.strip().splitlines()).strip()
    if not content or len(content) > 1800:
        raise ValueError("summary must contain 1-1800 characters")
    reject_private_text(content, config)
    guide = load_guide(guide_file, config)
    state = load_state(state_file)
    plan = build_plan(content, guide, state)
    if dry_run:
        return {**plan, "dry_run": True, "send_performed": False}
    if not confirmed_send:
        raise ValueError("real send requires --confirm-approved-send after review")
    if not config[bridge.TOKEN_ENV] or not bridge.token_rotation_status(config)[0]:
        raise ValueError("real send requires a bot credential with valid rotation attestation")
    with notice_lock(state_file):
        # Re-read state under the writer lock: concurrent create/update invalidates the plan.
        plan = build_plan(content, guide, load_state(state_file))
        if not dry_run_receipt or dry_run_receipt != plan["dry_run_receipt"]:
            raise ValueError("--dry-run-receipt does not match the current exact publication plan")
        verify_destination(config)
        body, content_type = multipart_payload(content, guide, plan)
        endpoint = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
        if plan["http_method"] == "PATCH":
            endpoint += "/" + str(plan["message_id"])
        request = urllib.request.Request(
            endpoint, data=body, method=str(plan["http_method"]),
            headers={"Content-Type": content_type, "User-Agent": "ObeliskBetaGuide/1",
                     "Authorization": "Bot " + config[bridge.TOKEN_ENV]},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                status = int(response.status)
                if not 200 <= status < 300:
                    raise ValueError(f"Discord returned HTTP {status}; no automatic retry")
                response_data = json.loads(response.read(1024 * 1024))
        except urllib.error.HTTPError as exc:
            # Never print Discord response bodies or silently POST after a PATCH failure.
            suffix = "; existing notice missing, review a new create plan" if exc.code == 404 else ""
            raise ValueError(f"Discord returned HTTP {exc.code}; no automatic retry{suffix}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ValueError("Discord delivery is uncertain; inspect the destination before retrying") from None
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Discord response is invalid; inspect the destination before retrying") from None
        message_id = response_data.get("id") if isinstance(response_data, dict) else None
        if (
            not isinstance(message_id, str) or not re.fullmatch(r"[0-9]{1,20}", message_id)
            or response_data.get("channel_id") != CHANNEL_ID
            or plan["http_method"] == "PATCH" and message_id != plan["message_id"]
        ):
            raise ValueError("Discord response does not match the destination; inspect before retrying")
        write_state(state_file, {
            "schema": STATE_SCHEMA, "guild_id": GUILD_ID, "channel_id": CHANNEL_ID,
            "message_id": message_id, "guide": guide.metadata(),
            "content_sha256": plan["content_sha256"],
            "updated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        })
    return {
        **plan, "dry_run": False, "send_performed": True, "http_status": status,
        "message_id": message_id,
        "message_url": f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/{message_id}",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guide-file", required=True, type=Path)
    parser.add_argument("--content-file", required=True, type=Path)
    parser.add_argument("--env-file", type=Path, default=bridge.DEFAULT_ENV_PATH)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dry-run-receipt")
    parser.add_argument("--confirm-approved-send", action="store_true")
    args = parser.parse_args(argv)
    try:
        content = read_regular_file(args.content_file, 8 * 1024).decode("utf-8")
        report = publish_guide(
            guide_file=args.guide_file, content=content, env_file=args.env_file,
            state_file=args.state_file, dry_run=args.dry_run,
            confirmed_send=args.confirm_approved_send, dry_run_receipt=args.dry_run_receipt,
        )
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
