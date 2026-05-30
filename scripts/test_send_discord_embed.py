#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "send_discord_embed.py"


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
            "Obelisk v0.1.0-rc.1",
            "--description",
            "Public plugin authors can test the minimal copied event surface.",
            "--status",
            "Release candidate",
            "--scope",
            "Public SDK surface",
            "--field",
            "Incluye=ChatMessageEvent minimo",
            "--field",
            "Validacion=Release gate completado",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        embed = payload["embeds"][0]
        self.assertEqual(payload["content"], "")
        self.assertEqual(embed["color"], 0x2ECC71)
        self.assertEqual(embed["fields"][0]["name"], "Estado")
        self.assertIn("major public", embed["footer"]["text"])

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
            "arkserver ventana aprobada",
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
        result = self.run_dry(
            "--channel",
            "community",
            "--title",
            "Bad",
            "--description",
            "https://discord.com/api/webhooks/123/secret",
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


if __name__ == "__main__":
    unittest.main()
