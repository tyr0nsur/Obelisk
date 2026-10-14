#!/usr/bin/env python3
"""Migration inspection tests use only synthetic operator-owned copies."""

import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest import mock

import obelisk_migrate as migrate


class MigrationInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def config(self, value, name="config.json", raw=False):
        path = self.root / name
        path.write_text(value if raw else json.dumps(value), encoding="utf-8")
        return path

    def shop_db(self, rows=None, extra_sql=None):
        path = self.root / "shop.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE Players (Id INTEGER PRIMARY KEY, SteamId INTEGER, Kits TEXT, Points INTEGER, TotalSpent INTEGER)")
        connection.executemany("INSERT INTO Players(SteamId,Kits,Points,TotalSpent) VALUES (?,?,?,?)", rows or [(76561198000000001, '{"starter":{"Amount":2}}', 150, 25)])
        if extra_sql:
            connection.executescript(extra_sql)
        connection.commit()
        connection.close()
        return path

    def permissions_db(self, groups=None, player_group="Default,", timed="", tribe=False):
        path = self.root / "permissions.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE Players (Id INTEGER PRIMARY KEY, SteamId INTEGER, Groups TEXT, TimedGroups TEXT)")
        connection.execute("CREATE TABLE Groups (Id INTEGER PRIMARY KEY, GroupName TEXT, Permissions TEXT)")
        connection.executemany("INSERT INTO Groups(GroupName,Permissions) VALUES (?,?)", groups or [("Default", "Shop.Buy,"), ("Admins", "*,")])
        connection.execute("INSERT INTO Players(SteamId,Groups,TimedGroups) VALUES (?,?,?)", (76561198000000001, player_group, timed))
        if tribe:
            connection.execute("CREATE TABLE Tribes (Id INTEGER PRIMARY KEY, TribeId INTEGER, Groups TEXT, TimedGroups TEXT)")
            connection.execute("INSERT INTO Tribes(TribeId,Groups,TimedGroups) VALUES (?,?,?)", (22, "Default,", ""))
        connection.commit()
        connection.close()
        return path

    def inspect(self, kind, path, namespace=None):
        return migrate.inspect("dry-run", [(kind, path)], namespace)

    def codes(self, report):
        return {issue["code"] for issue in report["issues"]}

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = migrate.main(list(map(str, args)))
        return code, output.getvalue()

    def test_text_only_shop_config_has_supported_format_without_live_apply(self):
        report = self.inspect("shop_config", self.config({"Messages": {"HelpMessage": "Información del servidor"}}))
        self.assertEqual(report["status"], "supported")
        self.assertFalse(report["live_apply_available"])
        self.assertFalse(report["authoritative_identity"])

    def test_permissions_mysql_is_inspected_without_connecting_or_granting_admin(self):
        path = self.config({"Database": "mysql", "MysqlPass": "private_password", "MysqlHost": "unreachable.invalid"})
        with mock.patch.object(sqlite3, "connect", side_effect=AssertionError("must not connect")):
            report = self.inspect("permissions_config", path)
        self.assertEqual(report["status"], "mapping_required")
        self.assertIn("remote_database_not_connected", self.codes(report))
        self.assertFalse(report["automatic_admin_import"])
        self.assertNotIn("private_password", migrate.serialize(migrate.public_report(report)))

    def test_conflicting_database_selectors_are_blocked(self):
        report = self.inspect("permissions_config", self.config({"Database": "sqlite", "UseMysql": True}))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("conflicting_database_selectors", self.codes(report))

    def test_invalid_database_and_boolean_selectors_are_blocked(self):
        for config in ({"Database": "postgres"}, {"UseMysql": 1}):
            with self.subTest(config=config):
                report = self.inspect("permissions_config", self.config(config))
                self.assertEqual(report["status"], "blocked")
        report = self.inspect("shop_config", self.config({"General": {"TimedPointsReward": {"Enabled": "true"}}}))
        self.assertIn("expected_boolean", self.codes(report))

    def test_shop_catalog_requires_permissions_and_delivery_mapping(self):
        path = self.config({"Kits": {"starter": {"Price": 20, "DefaultAmount": 3, "Items": [{"Amount": 1, "Blueprint": "synthetic_item"}]}}})
        report = self.inspect("shop_config", path)
        self.assertEqual(report["status"], "mapping_required")
        self.assertFalse(report["sources"][0]["summary"]["delivery_available"])

    def test_money_negative_fraction_float_boolean_and_overflow_are_rejected(self):
        for number in ("-1", "1.25", "2.0", "true", str(migrate.MAX_INTEGER + 1)):
            with self.subTest(number=number):
                path = self.config('{"Kits":{"starter":{"Price":' + number + '}}}', raw=True)
                report = self.inspect("shop_config", path)
                self.assertEqual(report["status"], "blocked")
                self.assertIn("money_or_count_not_exact_nonnegative_integer", self.codes(report))

    def test_integer_larger_than_double_precision_remains_exact(self):
        exact = (1 << 53) + 17
        report = self.inspect("shop_config", self.config({"Kits": {"starter": {"Price": exact}}}))
        self.assertEqual(report["sources"][0]["source_data"]["Kits"]["starter"]["Price"], exact)
        self.assertEqual(report["status"], "mapping_required")

    def test_decimal_is_preserved_exactly_and_never_silently_rounded(self):
        report = self.inspect("shop_config", self.config('{"Kits":{"starter":{"Price":1.00000000000000001}}}', raw=True))
        encoded = json.loads(migrate.serialize(report))
        self.assertEqual(encoded["sources"][0]["source_data"]["Kits"]["starter"]["Price"], {"decimal_exact": "1.00000000000000001"})
        self.assertEqual(report["status"], "blocked")

    def test_catalog_entry_named_price_is_not_treated_as_a_money_field(self):
        report = self.inspect("shop_config", self.config({"Kits": {"Price": {"Price": 2}}}))
        self.assertEqual(report["status"], "mapping_required")

    def test_unknown_nested_fields_preserved_privately_and_redacted(self):
        secret = "secret_76561198000000001"
        report = self.inspect("shop_config", self.config({"Kits": {"starter": {secret: {"token": secret}}}}))
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["unmapped_fields"][0]["raw_name"], secret)
        self.assertEqual(report["unmapped_fields"][0]["raw_value"], {"token": secret})
        self.assertNotIn(secret, migrate.serialize(migrate.public_report(report)))

    def test_admin_commands_are_never_executed_or_imported(self):
        marker = self.root / "command_was_executed"
        config = {"Kits": {"admin": {"Commands": [{"Command": "touch " + str(marker), "ExecuteAsAdmin": True}]}}}
        report = self.inspect("shop_config", self.config(config))
        self.assertIn("legacy_commands_or_admin_execution_not_imported", self.codes(report))
        self.assertFalse(marker.exists())
        self.assertFalse(report["automatic_admin_import"])

    def test_uninterpreted_gacha_overrides_are_blocked_and_preserved(self):
        value = {"extension": {"auth_token": "private"}}
        report = self.inspect("shop_config", self.config({"ShopItems": {"dino": {"GachaResources": value}}}))
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["unmapped_fields"][0]["raw_value"], value)

    def test_duplicate_json_fields_and_non_finite_numbers_are_blocked(self):
        for raw in ('{"Kits":{},"Kits":{}}', '{"Kits":{"x":{"Price":NaN}}}'):
            with self.subTest(raw=raw):
                self.assertEqual(self.inspect("shop_config", self.config(raw, raw=True))["status"], "blocked")

    def test_decimal_exponent_overflow_has_a_blocked_report_without_traceback(self):
        path = self.config('{"Kits":{"starter":{"Price":1e999999999999999999999999}}}', raw=True)
        code, output = self.cli("inspect", "--shop-config", path)
        self.assertEqual(code, 3)
        self.assertIn("invalid_json", output)

    def test_malformed_utf8_shape_and_excess_depth_are_blocked(self):
        path = self.root / "invalid.json"
        path.write_bytes(b"\xff")
        self.assertIn("invalid_config_utf8", self.codes(self.inspect("shop_config", path)))
        self.assertEqual(self.inspect("shop_config", self.config(["not", "an", "object"]))["status"], "blocked")
        nested = {"x": {}}
        for _ in range(35):
            nested = {"x": nested}
        self.assertIn("config_depth_exceeded", self.codes(self.inspect("shop_config", self.config(nested))))

    def test_unpaired_json_surrogate_is_blocked_and_report_stays_serializable(self):
        report = self.inspect("shop_config", self.config('{"Messages":{"HelpMessage":"\\ud800"}}', raw=True))
        self.assertEqual(report["status"], "blocked")
        self.assertIn("invalid_json_unicode", self.codes(report))
        self.assertEqual(json.loads(migrate.serialize(migrate.public_report(report)))["status"], "blocked")

    def test_sqlite_legacy_rows_have_no_native_account_authority(self):
        report = self.inspect("shop_db", self.shop_db(), "steam")
        self.assertEqual(report["status"], "mapping_required")
        row = report["sources"][0]["proposed_records"][0]
        self.assertEqual(row["declared_legacy_namespace"], "steam")
        self.assertFalse(row["activation_allowed"])
        self.assertFalse(report["authoritative_identity"])
        self.assertEqual(report["sources"][0]["summary"]["integer_totals"], {"Points": 150, "TotalSpent": 25})

    def test_nineteen_digit_subject_without_explicit_namespace_is_not_epic_or_steam(self):
        report = self.inspect("shop_db", self.shop_db([(1000000000000000001, "{}", 1, 0)]))
        self.assertIn("explicit_legacy_steam_namespace_required", self.codes(report))
        self.assertIsNone(report["sources"][0]["proposed_records"][0]["declared_legacy_namespace"])
        self.assertNotIn("epic", migrate.serialize(report).lower())

    def test_duplicate_accounts_are_conflicts_even_when_balances_equal(self):
        report = self.inspect("shop_db", self.shop_db([(76561198000000001, "{}", 10, 0)] * 2), "steam")
        self.assertIn("duplicate_legacy_account_conflict", self.codes(report))
        self.assertEqual(report["status"], "blocked")

    def test_negative_float_and_text_sqlite_balances_are_blocked(self):
        for number in (-1, 1.5, "9223372036854775808", "bad"):
            with self.subTest(number=number):
                path = self.shop_db([(76561198000000001, "{}", number, 0)])
                self.assertIn("balance_not_exact_nonnegative_integer", self.codes(self.inspect("shop_db", path, "steam")))
                path.unlink()

    def test_invalid_legacy_subjects_are_blocked(self):
        for value in (0, -1, "001", "EOS:account", 1.5):
            with self.subTest(value=value):
                # TEXT affinity would retain leading zeroes; direct parser must
                # reject them, independent of SQLite's integer affinity rules.
                with self.assertRaises(migrate.InspectionError):
                    migrate.subject(value)

    def test_real_kit_credit_shape_is_recognized_but_not_activated(self):
        report = self.inspect("shop_db", self.shop_db([(76561198000000001, '{"starter":{"Amount":7}}', 0, 0)]), "steam")
        self.assertNotIn("invalid_kit_credits", self.codes(report))
        self.assertEqual(report["status"], "mapping_required")

    def test_kit_credit_scalar_negative_and_unknown_fields_are_blocked(self):
        for kits in ('{"starter":7}', '{"starter":{"Amount":-1}}', '{"starter":{"Amount":3,"extension":"private"}}'):
            with self.subTest(kits=kits):
                path = self.shop_db([(76561198000000001, kits, 0, 0)])
                self.assertEqual(self.inspect("shop_db", path, "steam")["status"], "blocked")
                path.unlink()

    def test_permissions_admins_timed_groups_and_tribes_require_review(self):
        path = self.permissions_db(timed="0;2000000000;Admins,", tribe=True)
        report = self.inspect("permissions_db", path, "steam")
        self.assertEqual(report["status"], "mapping_required")
        self.assertFalse(report["automatic_admin_import"])
        self.assertTrue({"admin_or_wildcard_grant_requires_explicit_review", "timed_group_epoch_semantics_require_review", "tribe_cluster_namespace_and_membership_unmapped"} <= self.codes(report))

    def test_unknown_group_reference_and_case_conflict_are_blocked(self):
        path = self.permissions_db(player_group="Unknown,")
        self.assertIn("unknown_group_reference", self.codes(self.inspect("permissions_db", path, "steam")))
        path.unlink()
        path = self.permissions_db(groups=[("Default", ""), ("default", "")])
        self.assertIn("duplicate_group_name_conflict", self.codes(self.inspect("permissions_db", path, "steam")))

    def test_unknown_or_malformed_timed_membership_cannot_be_activated(self):
        for timed, expected in (("0;2000000000;Unknown,", "unknown_group_reference"), ("1.5;2000000000;Admins,", "unrecognized_timed_group_format"), ("2000000000;Admins,", "unrecognized_timed_group_format")):
            with self.subTest(timed=timed):
                path = self.permissions_db(timed=timed)
                self.assertIn(expected, self.codes(self.inspect("permissions_db", path, "steam")))
                path.unlink()

    def test_unknown_column_and_schema_objects_are_blocked_without_executing_views(self):
        path = self.shop_db(extra_sql='ALTER TABLE Players ADD COLUMN Secret TEXT; UPDATE Players SET Secret="private"; CREATE VIEW malicious AS SELECT load_extension("private");')
        report = self.inspect("shop_db", path, "steam")
        self.assertEqual(report["status"], "blocked")
        self.assertIn("unknown_field_preserved", self.codes(report))
        self.assertEqual(report["sources"][0]["proposed_records"][0]["source_data"]["Secret"], "private")
        self.assertNotIn("private", migrate.serialize(migrate.public_report(report)))

    def test_view_in_place_of_players_and_generated_columns_are_rejected(self):
        path = self.root / "view.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("CREATE VIEW Players AS SELECT load_extension('never_run')")
        connection.close()
        self.assertIn("database_required_tables_missing", self.codes(self.inspect("shop_db", path, "steam")))
        path = self.shop_db(extra_sql="ALTER TABLE Players ADD COLUMN Extension INTEGER GENERATED ALWAYS AS (Points+1)")
        self.assertIn("generated_or_hidden_column_not_supported", self.codes(self.inspect("shop_db", path, "steam")))

    def test_unknown_eos_column_is_not_reinterpreted_as_steam(self):
        path = self.root / "eos.sqlite"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE Players (Id INTEGER, EOSID TEXT, Kits TEXT, Points INTEGER, TotalSpent INTEGER)")
        connection.close()
        report = self.inspect("shop_db", path, "steam")
        self.assertIn("database_required_columns_missing", self.codes(report))
        self.assertEqual(report["unmapped_fields"][0]["raw_name"], "EOSID")

    def test_unicode_identifier_casefold_collision_cannot_replace_steam_id(self):
        path = self.shop_db(extra_sql='ALTER TABLE Players ADD COLUMN "ſteamId" INTEGER; UPDATE Players SET "ſteamId"=76561198000000002;')
        report = self.inspect("shop_db", path, "steam")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["sources"][0]["proposed_records"][0]["legacy_subject"], "76561198000000001")
        self.assertEqual(report["unmapped_fields"][0]["raw_name"], "ſteamId")

    def test_source_database_and_config_hashes_modes_and_directory_stay_unchanged(self):
        database = self.shop_db()
        config = self.config({"Mysql": {"MysqlPass": "private"}})
        before = {path: (path.read_bytes(), path.stat().st_mode) for path in (database, config)}
        names = set(self.root.iterdir())
        migrate.inspect("dry-run", [("shop_db", database), ("shop_config", config)], "steam")
        self.assertEqual(set(self.root.iterdir()), names)
        for path, state in before.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mode), state)

    def test_sqlite_only_receives_an_in_memory_copy(self):
        real_connect = sqlite3.connect
        calls = []
        def connect(path, *args, **kwargs):
            calls.append(path)
            return real_connect(path, *args, **kwargs)
        database = self.shop_db()
        with mock.patch.object(sqlite3, "connect", side_effect=connect):
            report = self.inspect("shop_db", database, "steam")
        self.assertEqual(calls, [":memory:"])
        self.assertEqual(report["status"], "mapping_required")

    def test_sidecar_and_dangling_sidecar_symlink_reject_live_snapshot(self):
        path = self.shop_db()
        sidecar = Path(str(path) + "-wal")
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                if symlink:
                    sidecar.symlink_to(self.root / "missing")
                else:
                    sidecar.write_bytes(b"not_read")
                self.assertIn("database_sidecars_require_clean_offline_snapshot", self.codes(self.inspect("shop_db", path, "steam")))
                sidecar.unlink()

    def test_row_limit_and_malformed_database_are_blocked(self):
        path = self.shop_db([(76561198000000001, "{}", 1, 0), (76561198000000002, "{}", 1, 0)])
        with mock.patch.object(migrate, "MAX_ROWS", 1):
            self.assertIn("database_row_limit_exceeded", self.codes(self.inspect("shop_db", path, "steam")))
        path.write_bytes(b"not sqlite")
        self.assertEqual(self.inspect("shop_db", path, "steam")["status"], "blocked")

    def test_large_kit_cells_and_python_processing_budget_are_blocked(self):
        path = self.shop_db([(76561198000000001, " " * (migrate.MAX_KIT_BYTES + 1), 0, 0)])
        self.assertIn("kit_json_size_limit_exceeded", self.codes(self.inspect("shop_db", path, "steam")))
        with mock.patch.object(migrate, "MAX_DATABASE_SECONDS", -1):
            self.assertIn("database_inspection_time_budget_exceeded", self.codes(self.inspect("shop_db", path, "steam")))
        path.unlink()
        path = self.shop_db([(76561198000000001, '{"a":{"Amount":1},"b":{"Amount":1}}', 0, 0)])
        with mock.patch.object(migrate, "MAX_KIT_ENTRIES", 1):
            self.assertIn("kit_entry_limit_exceeded", self.codes(self.inspect("shop_db", path, "steam")))

    def test_source_symlink_and_size_limit_are_blocked(self):
        source = self.config({})
        link = self.root / "link.json"
        link.symlink_to(source)
        self.assertIn("source_symlink_rejected", self.codes(self.inspect("shop_config", link)))
        with mock.patch.object(migrate, "MAX_CONFIG_BYTES", 1):
            self.assertIn("source_type_or_size_rejected", self.codes(self.inspect("shop_config", source)))

    def test_fifo_source_is_rejected_without_blocking_or_reading(self):
        path = self.root / "not_a_config"
        os.mkfifo(path)
        self.assertIn("source_type_or_size_rejected", self.codes(self.inspect("shop_config", path)))

    def test_racing_source_directory_symlink_cannot_redirect_the_read(self):
        original = self.root / "source-directory"
        original.mkdir()
        (original / "config.json").write_text("{}")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "config.json").write_text('{"secret":"never_read"}')
        real_open = os.open
        def open_racing(path, flags, *args, **kwargs):
            if path == "source-directory":
                original.rename(self.root / "saved-original")
                original.symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)
        with mock.patch.object(os, "open", side_effect=open_racing):
            report = self.inspect("shop_config", original / "config.json")
        self.assertIn("source_symlink_rejected", self.codes(report))
        self.assertNotIn("never_read", migrate.serialize(report))

    def test_changed_source_is_reported_not_claimed_coherent(self):
        path = self.config({})
        original = migrate.source_file
        calls = [0]
        def read(path, limit):
            calls[0] += 1
            resolved, content = original(path, limit)
            return resolved, content if calls[0] == 1 else content + b" "
        with mock.patch.object(migrate, "source_file", side_effect=read):
            report = self.inspect("shop_config", path)
        self.assertIn("source_changed_during_inspection", self.codes(report))

    def test_default_cli_redacts_password_account_and_input_path(self):
        path = self.shop_db()
        config = self.config({"Mysql": {"MysqlPass": "secret_password", "MysqlUser": "private_account"}})
        code, output = self.cli("inspect", "--shop-db", path, "--shop-config", config)
        self.assertEqual(code, 2)
        for secret in ("76561198000000001", "secret_password", "private_account", str(path)):
            self.assertNotIn(secret, output)
        self.assertTrue(json.loads(output)["redacted"])

    def test_sensitive_output_requires_explicit_private_file_and_never_stdout(self):
        path = self.config({"Mysql": {"MysqlPass": "secret_password"}})
        code, output = self.cli("inspect", "--shop-config", path, "--include-sensitive")
        self.assertEqual(code, 3)
        self.assertIn("sensitive_output_requires_private_file", output)
        destination = self.root / "private" / "nested" / "report.json"
        code, output = self.cli("dry-run", "--shop-config", path, "--output", destination, "--include-sensitive")
        self.assertEqual(code, 0)
        self.assertNotIn("secret_password", output)
        self.assertIn("secret_password", destination.read_text())
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(destination.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(destination.parent.parent.stat().st_mode), 0o700)

    def test_existing_output_and_nonprivate_directory_are_not_changed(self):
        source = self.config({})
        private = self.root / "private"
        private.mkdir(mode=0o700)
        destination = private / "existing.json"
        destination.write_text("preserve")
        code, _ = self.cli("inspect", "--shop-config", source, "--output", destination)
        self.assertEqual(code, 3)
        self.assertEqual(destination.read_text(), "preserve")
        unsafe = self.root / "shared"
        unsafe.mkdir(mode=0o755)
        code, output = self.cli("inspect", "--shop-config", source, "--output", unsafe / "new.json")
        self.assertEqual(code, 3)
        self.assertIn("output_parent_must_be_owned_mode_0700", output)
        self.assertFalse((unsafe / "new.json").exists())

    def test_output_symlink_parent_is_rejected_before_creating_directories(self):
        source = self.config({})
        real = self.root / "real"
        real.mkdir()
        link = self.root / "alias"
        link.symlink_to(real, target_is_directory=True)
        code, output = self.cli("inspect", "--shop-config", source, "--output", link / "new" / "report.json")
        self.assertEqual(code, 3)
        self.assertIn("output_symlink_rejected", output)
        self.assertFalse((real / "new").exists())

    def test_racing_output_directory_symlink_cannot_redirect_the_report(self):
        source = self.config({})
        private = self.root / "private"
        private.mkdir(mode=0o700)
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        real_open = os.open
        def open_racing(path, flags, *args, **kwargs):
            if path == "private":
                private.rename(self.root / "saved-private")
                private.symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, *args, **kwargs)
        with mock.patch.object(os, "open", side_effect=open_racing):
            code, output = self.cli("inspect", "--shop-config", source, "--output", private / "report.json")
        self.assertEqual(code, 3)
        self.assertIn("output_symlink_rejected", output)
        self.assertFalse((outside / "report.json").exists())

    def test_failure_output_does_not_echo_malicious_paths_or_unknown_options(self):
        secret = "secret_account_76561198000000001"
        code, output = self.cli("inspect", "--shop-db", self.root / secret)
        self.assertEqual(code, 3)
        self.assertNotIn(secret, output)
        code, output = self.cli("inspect", "--" + secret)
        self.assertEqual(code, 3)
        self.assertNotIn(secret, output)

    def test_epic_namespace_and_apply_options_are_not_available(self):
        for args in (("inspect", "--identity-namespace", "epic"), ("dry-run", "--apply")):
            with self.subTest(args=args):
                code, output = self.cli(*args)
                self.assertEqual(code, 3)
                self.assertIn("invalid_arguments", output)
        self.assertEqual(migrate.inspect("inspect", [])["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
