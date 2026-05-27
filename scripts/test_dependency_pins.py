#!/usr/bin/env python3
"""Guardrails for reproducible FetchContent dependency pins."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FULL_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def fetchcontent_tag(cmake_text: str, dependency: str) -> str:
    match = re.search(
        rf"FetchContent_Declare\(\s*{re.escape(dependency)}\s+.*?GIT_TAG\s+(?P<tag>\S+)",
        cmake_text,
        re.S,
    )
    if not match:
        raise AssertionError(f"missing FetchContent declaration for {dependency}")
    return match.group("tag")


class DependencyPinTests(unittest.TestCase):
    def test_subhook_uses_full_commit_sha_not_branch(self) -> None:
        cmake_text = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        tag = fetchcontent_tag(cmake_text, "subhook")

        self.assertRegex(tag, FULL_GIT_SHA_RE)
        self.assertNotIn(tag, {"master", "main", "HEAD"})

    def test_subhook_reproducibility_note_mentions_remaining_mirror_risk(self) -> None:
        note = (REPO_ROOT / "docs/research/2026-05-27-subhook-reproducibility.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("568d2e5a5d6013907e8008857968906b33ef3b7d", note)
        self.assertIn("mirror or vendored archive", note)


if __name__ == "__main__":
    unittest.main()
