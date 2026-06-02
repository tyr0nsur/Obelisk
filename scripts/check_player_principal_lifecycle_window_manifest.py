#!/usr/bin/env python3
"""Compatibility entry point for the player-principal lifecycle window manifest checker."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_player_identity_runtime_principal_lifecycle_window_manifest import (
    APPROVED_OFFLINE_WORKSPACE_ROOTS,
    Validation,
    build_report,
    load_manifest,
    main,
    validate_manifest,
)


if __name__ == "__main__":
    raise SystemExit(main())
