#!/usr/bin/env python3
"""Guardrails for reproducible FetchContent dependency pins."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FULL_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_FETCHCONTENT_PINS = {
    "fmt": "f5e54359df4c26b6230fc61d38aa294581393084",
    "spdlog": "7e635fca68d014934b4af8a1cf874f63989352b7",
    "subhook": "568d2e5a5d6013907e8008857968906b33ef3b7d",
}


def fetchcontent_tag(cmake_text: str, dependency: str) -> str:
    match = re.search(
        rf"FetchContent_Declare\(\s*{re.escape(dependency)}\s+.*?GIT_TAG\s+(?P<tag>\S+)",
        cmake_text,
        re.S,
    )
    if not match:
        raise AssertionError(f"missing FetchContent declaration for {dependency}")
    return match.group("tag")


def fetchcontent_dependencies(cmake_text: str) -> set[str]:
    return {
        match.group("dependency")
        for match in re.finditer(
            r"FetchContent_Declare\(\s*(?P<dependency>[A-Za-z0-9_-]+)\s+.*?GIT_REPOSITORY\s+",
            cmake_text,
            re.S,
        )
    }


class DependencyPinTests(unittest.TestCase):
    def test_fetchcontent_dependencies_use_full_commit_sha_not_branch_or_tag(self) -> None:
        cmake_text = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertEqual(fetchcontent_dependencies(cmake_text), set(EXPECTED_FETCHCONTENT_PINS))
        for dependency, expected_sha in EXPECTED_FETCHCONTENT_PINS.items():
            with self.subTest(dependency=dependency):
                tag = fetchcontent_tag(cmake_text, dependency)
                self.assertRegex(tag, FULL_GIT_SHA_RE)
                self.assertEqual(tag, expected_sha)
                self.assertNotIn(tag, {"master", "main", "HEAD"})

    def test_dependency_reproducibility_note_mentions_remaining_mirror_risk(self) -> None:
        note = (REPO_ROOT / "docs/research/2026-05-27-subhook-reproducibility.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("f5e54359df4c26b6230fc61d38aa294581393084", note)
        self.assertIn("7e635fca68d014934b4af8a1cf874f63989352b7", note)
        self.assertIn("568d2e5a5d6013907e8008857968906b33ef3b7d", note)
        self.assertIn("mirror or vendored archive", note)


if __name__ == "__main__":
    unittest.main()
