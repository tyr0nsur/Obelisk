#!/usr/bin/env python3

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_resource_handle_serials as scan


class ScanResourceHandleSerialsTests(unittest.TestCase):
    def test_summarizes_serial_and_flag_evidence(self) -> None:
        summary = scan.summarize_objects(
            [
                {
                    "index": 1,
                    "address": "0x1000",
                    "class_name": "Function",
                    "name": "Zero",
                    "flags": 0x81,
                    "fuobject_item": "0x2000",
                    "item_dword_0x8": 0,
                    "item_dword_0xC": 17,
                    "internal_index_matches": True,
                },
                {
                    "index": 2,
                    "address": "0x1010",
                    "class_name": "LinkerLoad",
                    "name": "Serial",
                    "flags": 0x100,
                    "fuobject_item": "0x2010",
                    "item_dword_0x8": 1001,
                    "item_dword_0xC": 23,
                    "internal_index_matches": True,
                },
                {
                    "index": 3,
                    "address": "0x1020",
                    "class_name": "LinkerLoad",
                    "name": "Serial2",
                    "flags": 0x4000,
                    "fuobject_item": "0x2020",
                    "item_dword_0x8": 1002,
                    "item_dword_0xC": 29,
                    "internal_index_matches": False,
                },
                {
                    "index": 4,
                    "address": "0x1030",
                    "class_name": "Class",
                    "name": "Missing",
                    "flags": None,
                    "fuobject_item": "0x2030",
                    "item_dword_0x8": None,
                    "item_dword_0xC": None,
                    "internal_index_matches": True,
                },
            ],
            sample_limit=1,
        )

        self.assertEqual(
            summary["totals"],
            {
                "objects_read": 4,
                "serial_zero": 1,
                "serial_nonzero": 2,
                "serial_missing": 1,
                "flags_0x100": 1,
                "flags_0x4000": 1,
                "flags_any": 2,
                "internal_index_mismatch": 1,
            },
        )
        self.assertEqual(summary["top_nonzero_serial_classes"], [("LinkerLoad", 2)])
        self.assertEqual(len(summary["nonzero_serial_samples"]), 1)
        self.assertEqual(summary["nonzero_serial_samples"][0]["item_dword_0x8"], 1001)
        self.assertEqual(len(summary["flag_mask_samples"]), 1)
        self.assertEqual(summary["flag_mask_samples"][0]["flags"], 0x100)

    def test_rejects_negative_sample_limit(self) -> None:
        with self.assertRaises(ValueError):
            scan.summarize_objects([], sample_limit=-1)


if __name__ == "__main__":
    unittest.main()
