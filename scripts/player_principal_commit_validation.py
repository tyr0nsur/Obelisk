#!/usr/bin/env python3
"""Validation helpers for player-principal lifecycle evidence identity."""

from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path


OBELISK_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ALL_ZERO_COMMIT = "0" * 40
REPO_ROOT = Path(__file__).resolve().parents[1]


@functools.lru_cache(maxsize=128)
def _commit_exists_in_repo(value: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{value}^{{commit}}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def is_reviewed_obelisk_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(OBELISK_GIT_COMMIT_RE.fullmatch(value))
        and value != ALL_ZERO_COMMIT
        and _commit_exists_in_repo(value)
    )
