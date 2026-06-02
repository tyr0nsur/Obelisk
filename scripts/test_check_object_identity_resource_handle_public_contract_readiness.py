#!/usr/bin/env python3
"""Tests for check_object_identity_resource_handle_public_contract_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_object_identity_resource_handle_public_contract_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "object_identity_resource_handle_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PUBLIC_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"


def run_checker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class ObjectIdentityResourceHandlePublicContractReadinessTests(unittest.TestCase):
    def test_current_contract_is_valid_planning_only_blocked(self) -> None:
        result = run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_resource_handle_ready"])
        self.assertFalse(report["post_callback_resource_handle_ready"])

    def test_rejects_decisions_that_enable_public_resource_handles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_header_allowed"] = True
            decisions["public_resource_handle_ready"] = True
            decisions["required_public_contract"] = ["ObeliskResourceHandle"]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_resource_handle_ready_not_false", report["blockers"])
        self.assertIn("required_public_contract_not_empty", report["blockers"])

    def test_rejects_positive_resource_handle_claim_in_decisions_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "ResourceHandle ready for public SDK lookup and post-callback object correlation."
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_resource_handle_ships_claim_in_decisions_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["release_claim"] = (
                "v1 ships ResourceHandle object identity for post-callback object correlation."
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("decisions_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_positive_resource_handle_metadata_in_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["metadata"] = {
                "resource_handle": "ready",
                "public_object_lookup_ready": True,
            }
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.decisions.metadata.resource_handle",
            report["blockers"],
        )
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.decisions.metadata.public_object_lookup_ready",
            report["blockers"],
        )

    def test_rejects_public_sdk_surface_promotion_or_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "stable"
                    surface["public_contract"] = ["ObeliskResourceHandle"]
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surface_status_not_post_v1", report["blockers"])
        self.assertIn("surface_support_tier_not_blocked", report["blockers"])
        self.assertIn("surface_public_contract_not_empty", report["blockers"])

    def test_rejects_positive_resource_handle_claim_in_surface_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "ResourceHandle ready for public SDK lookup and post-callback object correlation"
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_resource_handle_ships_claim_in_surface_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["evidence"]["claim"] = (
                        "v1 ships ResourceHandle object identity for post-callback object correlation."
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_promoted_descriptor_surface_resource_handle_contract_and_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.descriptors.v1":
                    surface["public_contract"].append("ObeliskResourceHandle")
                    surface["evidence"]["claim"] = (
                        "Descriptor metadata now includes public ResourceHandle lookup API readiness."
                    )
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                blocker.startswith("promoted_descriptor_surface_forbidden_public_contract:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )
        self.assertTrue(
            any(
                blocker.startswith("surface_positive_resource_handle_claim:")
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_rejects_positive_resource_handle_metadata_in_surface_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.object_identity_resource_handle.v1":
                    surface["resource_handle_ready"] = True
                    surface["object_lookup"] = "ready"
                    break
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "forbidden_positive_resource_handle_claim:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].resource_handle_ready",
            report["blockers"],
        )
        self.assertIn(
            "forbidden_positive_resource_handle_claim:"
            "$.surfaces[obelisk.object_identity_resource_handle.v1].object_lookup",
            report["blockers"],
        )

    def test_rejects_public_header_resource_handle_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                HEADER.read_text(encoding="utf-8")
                + "\ntypedef struct ObeliskResourceHandle { uint64_t id; } ObeliskResourceHandle;\n"
                + "bool ResolveResource(ObeliskResourceHandle handle, void** out);\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_object_identity_or_resource_handle_symbol", report["blockers"])

    def test_header_scan_ignores_comments_and_resource_kind_supersets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                "/* ObeliskResourceHandle, UObject, FName, GObjects remain blocked. */\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY (1ull << 0)\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)\n"
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP (1ull << 2)\n"
                "typedef struct ObeliskResourceKindDescriptor {\n"
                "  uint32_t resource_kind;\n"
                "  uint64_t flags;\n"
                "} ObeliskResourceKindDescriptor;\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])

    def test_rejects_public_events_that_turn_resource_kind_into_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = json.loads(PUBLIC_EVENTS.read_text(encoding="utf-8"))
            events["metadata_surfaces"][0]["descriptor_fields"].append("resource_handle")
            events["metadata_surfaces"][0]["resource_handle_ready"] = True
            events_path = write_json(root, "events.json", events)

            result = run_checker("--public-events", str(events_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("resource_kind_descriptor_identity_or_lookup_field_present", report["blockers"])
        self.assertIn(
            "forbidden_positive_resource_handle_claim:$.metadata_surfaces[0].resource_handle_ready",
            report["blockers"],
        )

    def test_rejects_symlinked_input_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "decisions.json"
            real.write_text(DECISIONS.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "decisions-link.json"
            link.symlink_to(real)

            result = run_checker("--decisions", str(link), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
