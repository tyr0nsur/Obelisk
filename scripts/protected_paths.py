#!/usr/bin/env python3
"""Shared protected-path predicates for offline Obelisk tooling."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
SERVER_ROOT_WRITE_OPT_IN_ENV = "OBELISK_ALLOW_SERVER_ROOT_WRITES"
TEST_APPROVED_OFFLINE_WORKSPACE_ENV = "OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"
ALLOW_TEST_WORKSPACE_PREFIXES_ENV = "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES"


@dataclass(frozen=True)
class ProtectedPathStatus:
    expanded: Path
    resolved: Path
    direct_under_protected_root: bool
    resolved_under_protected_root: bool
    approved_offline_workspace: bool

    @property
    def protected(self) -> bool:
        return (
            self.direct_under_protected_root or self.resolved_under_protected_root
        ) and not self.approved_offline_workspace


def is_under_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def approved_offline_workspace_roots(
    default: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
) -> tuple[Path, ...]:
    test_root = os.environ.get(TEST_APPROVED_OFFLINE_WORKSPACE_ENV)
    if os.environ.get(ALLOW_TEST_WORKSPACE_PREFIXES_ENV) == "1" and test_root:
        return (Path(test_root).expanduser(),)
    return default


def is_approved_offline_workspace_path(
    path: Path,
    *,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
) -> bool:
    expanded = path.expanduser()
    resolved = expanded.resolve()
    return any(
        expanded.is_absolute()
        and is_under_path(expanded, root)
        and is_under_path(resolved, root.resolve())
        for root in approved_roots
    )


def protected_path_status(
    path: Path,
    *,
    protected_root: Path = SERVER_ROOT,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
) -> ProtectedPathStatus:
    expanded = path.expanduser()
    resolved = expanded.resolve()
    protected = protected_root.resolve()
    direct_protected = expanded.is_absolute() and is_under_path(expanded, protected_root)
    resolved_protected = is_under_path(resolved, protected)
    approved = is_approved_offline_workspace_path(expanded, approved_roots=approved_roots)
    return ProtectedPathStatus(
        expanded=expanded,
        resolved=resolved,
        direct_under_protected_root=direct_protected,
        resolved_under_protected_root=resolved_protected,
        approved_offline_workspace=approved,
    )


def protected_path_blocked(
    path: Path,
    *,
    protected_root: Path = SERVER_ROOT,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
) -> tuple[bool, Path]:
    status = protected_path_status(
        path,
        protected_root=protected_root,
        approved_roots=approved_roots,
    )
    return status.protected, status.resolved


def server_root_write_allowed() -> bool:
    return os.environ.get(SERVER_ROOT_WRITE_OPT_IN_ENV) == "1"


def reject_server_root_write_without_opt_in(
    path: Path,
    label: str,
    *,
    protected_root: Path = SERVER_ROOT,
) -> None:
    expanded = path.expanduser()
    resolved = expanded.resolve()
    protected = protected_root.resolve()
    direct_protected = expanded.is_absolute() and is_under_path(expanded, protected_root)
    resolved_protected = is_under_path(resolved, protected)
    if (direct_protected or resolved_protected) and not server_root_write_allowed():
        raise SystemExit(
            f"{label} must not write under {protected_root} unless "
            f"{SERVER_ROOT_WRITE_OPT_IN_ENV}=1 is set: {resolved}"
        )


def first_symlink_component(path: Path) -> Path | None:
    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() else expanded.absolute()
    current = Path(candidate.anchor) if candidate.anchor else Path()
    parts = candidate.parts[1:] if candidate.anchor else candidate.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def reject_symlink_component(path: Path, label: str) -> None:
    symlink = first_symlink_component(path)
    if symlink is not None:
        raise SystemExit(f"{label} must not be a symlink: {symlink}")


def reject_protected_input_path(
    path: Path,
    label: str,
    *,
    protected_root: Path = SERVER_ROOT,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
    message: str | None = None,
) -> Path:
    blocked, resolved = protected_path_blocked(
        path,
        protected_root=protected_root,
        approved_roots=approved_roots,
    )
    if blocked:
        if message is None:
            message = f"{label} must not read from protected server root {protected_root}: {resolved}"
        raise SystemExit(message)
    return resolved


def protected_input_path_blockers(
    path: Path,
    *,
    protected_root: Path = SERVER_ROOT,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
) -> list[dict[str, str]]:
    status = protected_path_status(
        path,
        protected_root=protected_root,
        approved_roots=approved_roots,
    )
    if not status.protected:
        return []
    if status.direct_under_protected_root:
        return [
            {
                "reason": "path_under_live_server_root",
                "detail": "copy evidence under /servidor/ark/workspace-offline before analysis",
            }
        ]
    return [
        {
            "reason": "resolved_path_under_live_server_root",
            "detail": "resolved evidence path is not under /servidor/ark/workspace-offline",
        }
    ]


def reject_protected_output_path(
    path: Path,
    label: str,
    *,
    protected_root: Path = SERVER_ROOT,
    approved_roots: tuple[Path, ...] = APPROVED_OFFLINE_WORKSPACE_ROOTS,
    message: str | None = None,
) -> Path:
    blocked, resolved = protected_path_blocked(
        path,
        protected_root=protected_root,
        approved_roots=approved_roots,
    )
    if blocked:
        if message is None:
            message = f"{label} must not write under protected server root {protected_root}: {resolved}"
        raise SystemExit(message)
    return resolved
