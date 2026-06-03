#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "send_discord_embed.py"

_SPEC = importlib.util.spec_from_file_location("send_discord_embed", SCRIPT)
assert _SPEC is not None
send_discord_embed = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(send_discord_embed)


class SendDiscordEmbedTests(unittest.TestCase):
    def run_dry(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--dry-run", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_builds_community_embed_without_webhook(self) -> None:
        result = self.run_dry(
            "--channel",
            "community",
            "--title",
            "Obelisk SDK progress: plugin-author RC surface",
            "--description",
            "Obelisk is moving toward a Linux SDK for ARK modders with copied plugin APIs that do not expose UE internals.",
            "--status",
            "Scoped release-candidate SDK milestone",
            "--scope",
            "Plugin-author ABI slices; not a v1.0 stable, complete, full, or production SDK claim.",
            "--field",
            "For modders=Build external plugins against the installed SDK package and promoted copied-data callbacks.",
            "--field",
            "Next priority=Promote additional surfaces only after second-source evidence and SDK ownership gates pass.",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        embed = payload["embeds"][0]
        self.assertEqual(payload["content"], "")
        self.assertEqual(embed["color"], 0x2ECC71)
        self.assertEqual(embed["fields"][0]["name"], "Estado")
        self.assertIn("major public", embed["footer"]["text"])
        rendered = json.dumps(payload)
        self.assertIn("ARK modders", rendered)
        self.assertNotIn("minimal copied event " + "surface", rendered)
        self.assertNotIn("Release gate " + "completado", rendered)

    def test_community_fixture_stays_modder_facing_not_internal_validation(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        forbidden_fixture_phrases = (
            "base " + "pequena",
            "base " + "pequeña",
            "minimal copied event " + "surface",
            "release gate " + "completed",
            "Release gate " + "completado",
            "internal " + "validation",
        )
        for phrase in forbidden_fixture_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, text)

    def test_builds_beta_embed_with_beta_color(self) -> None:
        result = self.run_dry(
            "--channel",
            "beta-test",
            "--title",
            "Prueba acotada de chat",
            "--description",
            "Ventana aprobada para validar entrega de eventos copiados.",
            "--status",
            "Beta activa",
            "--scope",
            "instancia nombrada en brief aprobado",
            "--field",
            "Accion=Enviar mensajes de chat global",
            "--field",
            "Privacidad=Sin publicar texto de jugadores",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        embed = json.loads(result.stdout)["embeds"][0]
        self.assertEqual(embed["color"], 0x3498DB)
        self.assertIn("in-game test", embed["footer"]["text"])

    def test_rejects_webhook_text_in_embed(self) -> None:
        webhook_text = "https://" + "discord.com/" + "api/webhooks" + "/123/secret"
        result = self.run_dry(
            "--channel",
            "community",
            "--title",
            "Bad",
            "--description",
            webhook_text,
            "--status",
            "Blocked",
            "--scope",
            "Guardrail",
            "--field",
            "A=B",
            "--field",
            "C=D",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden phrase", result.stderr)

    def test_rejects_forbidden_text_in_content(self) -> None:
        result = self.run_dry(
            "--channel",
            "community",
            "--title",
            "Obelisk update",
            "--description",
            "Public update for plugin authors.",
            "--status",
            "Blocked",
            "--scope",
            "Guardrail",
            "--content",
            "contains token value",
            "--field",
            "A=B",
            "--field",
            "C=D",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden phrase", result.stderr)

    def test_rejects_internal_status_phrases_in_embed_text(self) -> None:
        forbidden_cases = (
            ("description", "Internal validation passed for SDK JSON"),
            ("status", "Agent status: route JSON is valid"),
            ("scope", "Release gate completed during routine validation"),
            ("field", "Evidence=SDK JSON blocked as expected"),
            ("description", "Validation passed for release checks"),
            ("status", "Gate passed for package layout"),
            ("scope", "Route valid and SDK blocked"),
            ("field", "Suite=tests passed"),
        )

        for location, phrase in forbidden_cases:
            with self.subTest(location=location):
                args = [
                    "--channel",
                    "community",
                    "--title",
                    "Obelisk update",
                    "--description",
                    "Public update for plugin authors.",
                    "--status",
                    "Approved milestone",
                    "--scope",
                    "Community update",
                    "--field",
                    "A=B",
                    "--field",
                    "C=D",
                ]
                if location == "description":
                    args[args.index("--description") + 1] = phrase
                elif location == "status":
                    args[args.index("--status") + 1] = phrase
                elif location == "scope":
                    args[args.index("--scope") + 1] = phrase
                elif location == "field":
                    args[args.index("A=B")] = phrase

                result = self.run_dry(*args)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden phrase", result.stderr)

    def test_rejects_reserved_custom_field_names(self) -> None:
        result = self.run_dry(
            "--channel",
            "community",
            "--title",
            "Obelisk update",
            "--description",
            "Public update for plugin authors.",
            "--status",
            "In progress",
            "--scope",
            "SDK",
            "--field",
            "Estado=Duplicated heading",
            "--field",
            "Impacto=Clearer embeds",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reserved names", result.stderr)

    def test_test_fixtures_do_not_store_webhook_endpoint_literals(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("discord.com/" + "api/webhooks", source)
        self.assertNotIn("discordapp.com/" + "api/webhooks", source)

    def test_channel_webhooks_are_loaded_from_their_own_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "discord-webhooks.env"
            env_file.write_text(
                "\n".join(
                    [
                        "OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL" + "=https://example.invalid/community",
                        "OBELISK_BETA_TEST_WEBHOOK_URL" + "=https://example.invalid/beta-test",
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                community = send_discord_embed.load_webhook_url(
                    argparse.Namespace(channel="community", env_file=env_file)
                )
                beta_test = send_discord_embed.load_webhook_url(
                    argparse.Namespace(channel="beta-test", env_file=env_file)
                )

        self.assertEqual(community, "https://example.invalid/community")
        self.assertEqual(beta_test, "https://example.invalid/beta-test")

    def test_environment_webhook_overrides_local_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "discord-webhooks.env"
            env_file.write_text(
                "OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL"
                + "=https://example.invalid/local\n",
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {"OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL": "https://example.invalid/process"},
                clear=True,
            ):
                webhook_url = send_discord_embed.load_webhook_url(
                    argparse.Namespace(channel="community", env_file=env_file)
                )

        self.assertEqual(webhook_url, "https://example.invalid/process")

    def test_missing_channel_webhook_does_not_fall_back_to_other_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / "discord-webhooks.env"
            env_file.write_text(
                "OBELISK_BETA_TEST_WEBHOOK_URL"
                + "=https://example.invalid/beta-test\n",
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(SystemExit) as raised:
                    send_discord_embed.load_webhook_url(
                        argparse.Namespace(channel="community", env_file=env_file)
                    )

        self.assertIn("OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL", str(raised.exception))

    def test_real_send_requires_explicit_confirmation_and_matching_scope(self) -> None:
        base_args = [
            "--channel",
            "community",
            "--title",
            "Obelisk update",
            "--description",
            "Public update for plugin authors.",
            "--status",
            "Approved milestone",
            "--scope",
            "Community update",
            "--field",
            "A=B",
            "--field",
            "C=D",
        ]
        missing_confirm = subprocess.run(
            [sys.executable, str(SCRIPT), *base_args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(missing_confirm.returncode, 0)
        self.assertIn("--confirm-approved-send", missing_confirm.stderr)

        wrong_scope = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                *base_args,
                "--confirm-approved-send",
                "--approval-scope",
                "beta-test",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(wrong_scope.returncode, 0)
        self.assertIn("--approval-scope matches --channel", wrong_scope.stderr)

    def test_real_send_with_confirmation_uses_matching_webhook(self) -> None:
        args = [
            "--channel",
            "community",
            "--title",
            "Obelisk update",
            "--description",
            "Public update for plugin authors.",
            "--status",
            "Approved milestone",
            "--scope",
            "Community update",
            "--field",
            "A=B",
            "--field",
            "C=D",
            "--confirm-approved-send",
            "--approval-scope",
            "community",
        ]

        with (
            mock.patch.object(send_discord_embed, "load_webhook_url", return_value="https://example.invalid/webhook") as load,
            mock.patch.object(send_discord_embed, "send_payload") as send,
        ):
            rc = send_discord_embed.main(args)

        self.assertEqual(0, rc)
        load.assert_called_once()
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
