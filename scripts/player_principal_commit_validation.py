#!/usr/bin/env python3
"""Validation helpers for player-principal lifecycle evidence identity."""

from __future__ import annotations

import re


OBELISK_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ALL_ZERO_COMMIT = "0" * 40


def is_reviewed_obelisk_commit(value: object) -> bool:
    return isinstance(value, str) and bool(OBELISK_GIT_COMMIT_RE.fullmatch(value)) and value != ALL_ZERO_COMMIT

