#!/usr/bin/env python3
"""Mock-only publication tests: no configured operator credentials or Discord IO."""

from __future__ import annotations

from contextlib import contextmanager
from email import policy
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_discord_beta_guide as publisher


class FakeResponse:
    status = 200

    def __init__(self, value):
        self.body = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, max_bytes=-1):
        return self.body if max_bytes < 0 else self.body[:max_bytes]


class DiscordBetaGuideTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.guide = self.root / "beta-guide.md"
        self.guide_bytes = "# Guía beta\nEvidencia pendiente: /ping, /homes.\n".encode("utf-8")
        self.guide.write_bytes(self.guide_bytes)
        self.state = self.root / "notice" / "announcements-notice.json"
        self.config = {
            publisher.bridge.TOKEN_ENV: "unit-test-private-bot-credential",
            publisher.bridge.ROTATED_TOKEN_AT_ENV: "2026-06-07T00:00:00Z",
            publisher.bridge.GUILD_ENV: publisher.bridge.EXPECTED_GUILD_ID,
            publisher.bridge.BETA_CHANNEL_ENV: publisher.bridge.EXPECTED_CHANNEL_ID,
            publisher.bridge.SALT_ENV: "",
        }
        env = os.environ.copy()
        for key in tuple(env):
            if key.startswith("ARK") or key.startswith("OBELISK"):
                env.pop(key, None)
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, env, clear=True).start()
        mock.patch.object(publisher.bridge, "merged_config", return_value=self.config).start()
        self.requests = []
        self.transport = mock.patch.object(
            publisher.urllib.request, "urlopen", side_effect=self.fake_transport,
        ).start()

    def fake_transport(self, request, timeout=0):
        self.requests.append(request)
        if request.get_method() == "GET":
            return FakeResponse({"id": publisher.CHANNEL_ID, "guild_id": publisher.GUILD_ID, "type": 5})
        return FakeResponse({"id": "1234567890123456789", "channel_id": publisher.CHANNEL_ID})

    def publish(self, **kwargs):
        return publisher.publish_guide(
            guide_file=self.guide, content="Guía beta completa adjunta.", state_file=self.state,
            **kwargs,
        )

    def send(self):
        plan = self.publish()
        return self.publish(dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"])

    def seed_state(self):
        self.state.parent.mkdir(mode=0o700)
        value = {
            "schema": publisher.STATE_SCHEMA, "guild_id": publisher.GUILD_ID,
            "channel_id": publisher.CHANNEL_ID, "message_id": "1234567890123456789",
        }
        self.state.write_text(json.dumps(value))
        self.state.chmod(0o600)
        return value

    def parsed_request(self):
        request = self.requests[-1]
        message = BytesParser(policy=policy.default).parsebytes(
            ("Content-Type: " + request.get_header("Content-type") + "\r\nMIME-Version: 1.0\r\n\r\n").encode()
            + request.data
        )
        parts = list(message.iter_parts())
        payload = json.loads(parts[0].get_payload(decode=True))
        return parts, payload

    def test_dry_run_is_offline_and_contains_only_guide_fingerprint(self):
        plan = self.publish()
        self.assertFalse(self.transport.called)
        self.assertFalse(self.state.parent.exists())
        self.assertEqual(plan["http_method"], "POST")
        self.assertEqual(plan["guild_id"], publisher.GUILD_ID)
        self.assertEqual(plan["guide"]["sha256"], hashlib.sha256(self.guide_bytes).hexdigest())
        self.assertEqual(plan["guide"]["byte_length"], len(self.guide_bytes))
        rendered = json.dumps(plan)
        self.assertNotIn(str(self.guide), rendered)
        self.assertNotIn(self.config[publisher.bridge.TOKEN_ENV], rendered)
        self.assertNotIn("Evidencia pendiente", rendered)
        self.assertFalse(plan["counts_as_gameplay_acceptance"])

    def test_create_multipart_preserves_exact_bytes_and_disables_mentions(self):
        report = self.send()
        self.assertEqual([r.get_method() for r in self.requests], ["GET", "POST"])
        self.assertEqual(self.requests[0].full_url, "https://discord.com/api/v10/channels/" + publisher.CHANNEL_ID)
        parts, payload = self.parsed_request()
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0].get_param("name", header="content-disposition"), "payload_json")
        self.assertEqual(parts[1].get_param("name", header="content-disposition"), "files[0]")
        self.assertEqual(parts[1].get_filename(), self.guide.name)
        self.assertEqual(parts[1].get_payload(decode=True), self.guide_bytes)
        self.assertEqual(payload["attachments"], [{"id": 0, "filename": self.guide.name}])
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertEqual(payload["components"], [])
        self.assertTrue(payload["enforce_nonce"])
        self.assertEqual(payload["nonce"], report["nonce"])
        self.assertLessEqual(len(payload["nonce"]), 25)
        self.assertEqual(stat.S_IMODE(self.state.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.state.stat().st_mode), 0o600)
        self.assertEqual(json.loads(self.state.read_text())["message_id"], report["message_id"])

    def test_update_targets_same_message_and_replaces_old_attachments(self):
        self.seed_state()
        report = self.send()
        self.assertEqual([r.get_method() for r in self.requests], ["GET", "PATCH"])
        self.assertTrue(self.requests[-1].full_url.endswith("/1234567890123456789"))
        parts, payload = self.parsed_request()
        self.assertEqual(payload["attachments"], [{"id": 0, "filename": self.guide.name}])
        self.assertNotIn("nonce", payload)
        self.assertNotIn("enforce_nonce", payload)
        self.assertEqual(report["http_method"], "PATCH")

    def test_changed_guide_bytes_invalidates_receipt_before_network(self):
        plan = self.publish()
        self.guide.write_bytes(self.guide_bytes + b"A new test.\n")
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            self.publish(dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"])
        self.assertFalse(self.transport.called)

    def test_changed_filename_invalidates_receipt_before_network(self):
        plan = self.publish()
        renamed = self.guide.with_name("another-guide.md")
        self.guide.rename(renamed)
        self.guide = renamed
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            self.publish(dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"])
        self.assertFalse(self.transport.called)

    def test_changed_summary_invalidates_receipt_before_network(self):
        plan = self.publish()
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            publisher.publish_guide(
                guide_file=self.guide, content="Changed summary", state_file=self.state,
                dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"],
            )
        self.assertFalse(self.transport.called)

    def test_concurrent_state_create_invalidates_original_create_plan(self):
        plan = self.publish()
        self.seed_state()
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            self.publish(dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"])
        self.assertFalse(self.transport.called)

    def test_state_is_rechecked_inside_writer_lock(self):
        plan = self.publish()

        @contextmanager
        def racing_writer(path):
            self.seed_state()
            yield

        with mock.patch.object(publisher, "notice_lock", side_effect=racing_writer):
            with self.assertRaisesRegex(ValueError, "receipt does not match"):
                self.publish(dry_run=False, confirmed_send=True, dry_run_receipt=plan["dry_run_receipt"])
        self.assertFalse(self.transport.called)

    def test_send_requires_confirmation_and_receipt(self):
        with self.assertRaisesRegex(ValueError, "confirm-approved-send"):
            self.publish(dry_run=False)
        with self.assertRaisesRegex(ValueError, "receipt does not match"):
            self.publish(dry_run=False, confirmed_send=True)
        self.assertFalse(self.transport.called)

    def test_send_requires_rotation_attestation_without_echoing_credential(self):
        self.config[publisher.bridge.ROTATED_TOKEN_AT_ENV] = ""
        with self.assertRaisesRegex(ValueError, "rotation attestation") as raised:
            self.send()
        self.assertNotIn(self.config[publisher.bridge.TOKEN_ENV], str(raised.exception))
        self.assertFalse(self.transport.called)

    def test_invalid_utf8_rejected_before_network(self):
        self.guide.write_bytes(b"\xff")
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            self.publish()
        self.assertFalse(self.transport.called)

    def test_oversize_rejected_before_network(self):
        self.guide.write_bytes(b"a" * (publisher.GUIDE_MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "maximum byte length"):
            self.publish()
        self.assertFalse(self.transport.called)

    def test_empty_guide_and_control_characters_rejected(self):
        for data, message in [(b"\n", "non-empty"), (b"text\x00", "control characters")]:
            with self.subTest(data=data):
                self.guide.write_bytes(data)
                with self.assertRaisesRegex(ValueError, message):
                    self.publish()

    def test_symlink_file_and_ancestor_rejected(self):
        linked = self.root / "linked.md"
        linked.symlink_to(self.guide)
        with self.assertRaisesRegex(SystemExit, "symlink"):
            publisher.load_guide(linked, self.config)
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(SystemExit, "symlink"):
            publisher.load_guide(alias / self.guide.name, self.config)
        self.assertFalse(self.transport.called)

    def test_directory_and_fifo_are_rejected_without_blocking(self):
        directory = self.root / "directory.md"
        directory.mkdir()
        fifo = self.root / "pipe.md"
        os.mkfifo(fifo)
        for path in (directory, fifo):
            with self.subTest(path=path.name):
                with self.assertRaisesRegex(ValueError, "regular file"):
                    publisher.load_guide(path, self.config)

    def test_unsafe_filename_rejected(self):
        for name in ['bad"name.md', "non-markdown.txt", "é.md"]:
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(self.guide_bytes)
                with self.assertRaisesRegex(ValueError, "filename"):
                    publisher.load_guide(path, self.config)

    def test_private_values_and_mentions_rejected_without_echoing_them(self):
        for value in [
            "password=placeholder", "203.0.113.7", "1234567890123456789", "0x12345678",
            "@everyone", "<@&1234>", "https://discord.com\x2fapi/webhooks/placeholder",
            self.config[publisher.bridge.TOKEN_ENV],
        ]:
            with self.subTest(kind=value[:8]):
                self.guide.write_text("Guide " + value)
                with self.assertRaises(ValueError) as raised:
                    self.publish()
                self.assertNotIn(value, str(raised.exception))
        self.assertFalse(self.transport.called)

    def test_private_password_from_environment_rejected(self):
        private_value = "unit-test-runtime-password"
        with mock.patch.dict(os.environ, {"ARK_SERVER_PASSWORD": private_value}):
            self.guide.write_text("Guide " + private_value)
            with self.assertRaisesRegex(ValueError, "configured private value"):
                self.publish()

    def test_wrong_destination_guild_is_rejected_before_mutation(self):
        self.transport.side_effect = lambda request, timeout: FakeResponse({
            "id": publisher.CHANNEL_ID, "guild_id": publisher.bridge.EXPECTED_GUILD_ID, "type": 5,
        })
        with self.assertRaisesRegex(ValueError, "selected guild and channel"):
            self.send()
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(self.transport.call_args.args[0].get_method(), "GET")
        self.assertFalse(self.state.exists())

    def test_update_404_does_not_create_or_retry(self):
        old_state = self.seed_state()

        def missing_update(request, timeout):
            if request.get_method() == "GET":
                return self.fake_transport(request, timeout)
            self.requests.append(request)
            raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)

        self.transport.side_effect = missing_update
        with self.assertRaisesRegex(ValueError, "existing notice missing"):
            self.send()
        self.assertEqual([r.get_method() for r in self.requests], ["GET", "PATCH"])
        self.assertEqual(json.loads(self.state.read_text()), old_state)

    def test_rate_limit_never_retries(self):
        def rate_limit(request, timeout):
            if request.get_method() == "GET":
                return self.fake_transport(request, timeout)
            self.requests.append(request)
            raise urllib.error.HTTPError(request.full_url, 429, "limited", {}, None)

        self.transport.side_effect = rate_limit
        with self.assertRaisesRegex(ValueError, "HTTP 429; no automatic retry"):
            self.send()
        self.assertEqual([r.get_method() for r in self.requests], ["GET", "POST"])
        self.assertFalse(self.state.exists())

    def test_wrong_message_response_does_not_write_state(self):
        def wrong_response(request, timeout):
            if request.get_method() == "GET":
                return self.fake_transport(request, timeout)
            return FakeResponse({"id": "12345", "channel_id": publisher.bridge.EXPECTED_CHANNEL_ID})

        self.transport.side_effect = wrong_response
        with self.assertRaisesRegex(ValueError, "does not match the destination"):
            self.send()
        self.assertFalse(self.state.exists())

    def test_state_with_wrong_destination_is_rejected_offline(self):
        value = self.seed_state()
        value["guild_id"] = publisher.bridge.EXPECTED_GUILD_ID
        self.state.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "configured destination"):
            self.publish()
        self.assertFalse(self.transport.called)


if __name__ == "__main__":
    unittest.main()
