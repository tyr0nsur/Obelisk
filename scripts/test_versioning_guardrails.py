#!/usr/bin/env python3
"""Guardrails for pre-release versioning language."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class VersioningGuardrailTests(unittest.TestCase):
    def test_public_docs_link_versioning_policy(self) -> None:
        for relative in ("README.md", "docs/STATUS.md", "docs/RELEASE.md"):
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("docs/VERSIONING.md" if relative == "README.md" else "VERSIONING.md", text)

    def test_versioning_policy_keeps_current_line_dev(self) -> None:
        text = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("0.1.0-dev", text)
        self.assertIn("no `v0.1.0` release is", text)

    def test_release_doc_does_not_claim_current_stable_release(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        self.assertIn("not ready for a production-stable release", text)
        self.assertRegex(text, re.compile(r"git tag -a v0\.1\.0", re.M))


if __name__ == "__main__":
    unittest.main()
