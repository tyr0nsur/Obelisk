#!/usr/bin/env python3
"""Tests for shared protected path helpers."""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import protected_paths


class ProtectedPathsTests(unittest.TestCase):
    def test_rejects_direct_path_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            protected.mkdir()
            path = protected / "live.log"

            with self.assertRaisesRegex(SystemExit, "must not read"):
                protected_paths.reject_protected_input_path(path, "log", protected_root=protected)

    def test_rejects_symlink_resolving_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            protected.mkdir()
            target = protected / "live.log"
            target.write_text("live", encoding="utf-8")
            link = root / "link.log"
            link.symlink_to(target)

            with self.assertRaisesRegex(SystemExit, "must not read"):
                protected_paths.reject_protected_input_path(link, "log", protected_root=protected)

    def test_rejects_textually_protected_symlink_resolving_outside(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            protected.mkdir()
            outside = root / "outside.log"
            outside.write_text("offline", encoding="utf-8")
            link = protected / "outward.log"
            link.symlink_to(outside)

            with self.assertRaisesRegex(SystemExit, "must not read"):
                protected_paths.reject_protected_input_path(link, "log", protected_root=protected)

    def test_allows_direct_path_under_approved_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            path = workspace / "snapshot.json"
            path.write_text("{}", encoding="utf-8")

            resolved = protected_paths.reject_protected_input_path(
                path,
                "snapshot",
                protected_root=protected,
                approved_roots=(workspace,),
            )

        self.assertEqual(path.resolve(), resolved)

    def test_rejects_workspace_path_that_resolves_outside(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            outside = root / "outside.log"
            outside.write_text("offline", encoding="utf-8")
            link = workspace / "outward.log"
            link.symlink_to(outside)

            with self.assertRaisesRegex(SystemExit, "must not read"):
                protected_paths.reject_protected_input_path(
                    link,
                    "snapshot",
                    protected_root=protected,
                    approved_roots=(workspace,),
                )

    def test_allows_similar_prefix_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            protected.mkdir()
            sibling = root / "server-not-live" / "snapshot.json"
            sibling.parent.mkdir()
            sibling.write_text("{}", encoding="utf-8")

            resolved = protected_paths.reject_protected_input_path(
                sibling,
                "snapshot",
                protected_root=protected,
            )

        self.assertEqual(sibling.resolve(), resolved)

    def test_first_symlink_component_reports_nearest_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)

            self.assertEqual(
                link,
                protected_paths.first_symlink_component(link / "nested" / "snapshot.json"),
            )

    def test_reject_symlink_component_fails_before_resolving_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)

            with self.assertRaisesRegex(SystemExit, r"--source must not be a symlink: .*link"):
                protected_paths.reject_symlink_component(link / "snapshot.json", "--source")

    def test_reject_server_root_write_requires_explicit_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected = Path(tmp) / "server"
            protected.mkdir()
            output = protected / "workspace-offline" / "out.json"

            with mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(SystemExit, "must not write"):
                    protected_paths.reject_server_root_write_without_opt_in(
                        output,
                        "--output",
                        protected_root=protected,
                    )

            with mock.patch.dict(
                "os.environ",
                {protected_paths.SERVER_ROOT_WRITE_OPT_IN_ENV: "1"},
                clear=True,
            ):
                protected_paths.reject_server_root_write_without_opt_in(
                    output,
                    "--output",
                    protected_root=protected,
                )


if __name__ == "__main__":
    unittest.main()
