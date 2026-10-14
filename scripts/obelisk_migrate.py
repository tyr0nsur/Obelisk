#!/usr/bin/env python3
"""Inspect operator-owned ASE plugin copies; never apply or contact a server.

Schema facts: ArkServerApi/ASE-Plugins commit
66faba2e46b5c5f4597fd72b6ac6eda838708569 (see docs/ARKAPI_MIGRATION.md).
This is an original parser/report format, not copied plugin implementation.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, DecimalException
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time


SCHEMA = "obelisk.native-migration-inspection.v1"
MAX_INTEGER = (1 << 63) - 1
MAX_SUBJECT = (1 << 64) - 1
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_DB_BYTES = 128 * 1024 * 1024
MAX_ROWS = 10000
MAX_KIT_BYTES = 65536
MAX_KIT_ENTRIES = 1000
MAX_DATABASE_SECONDS = 2.0
SOURCE_COMMIT = "66faba2e46b5c5f4597fd72b6ac6eda838708569"

PERMISSIONS_CONFIG = {
    "Database", "UseMysql", "MysqlHost", "MysqlUser", "MysqlPass", "MysqlDB",
    "MysqlPort", "DbPathOverride", "ClusterSyncTime", "MysqlPlayersTable",
    "MysqlGroupsTable", "MysqlTribesTable",
}
MYSQL = {"UseMysql", "MysqlHost", "MysqlUser", "MysqlPass", "MysqlDB", "MysqlPort"}
GENERAL = {
    "Discord", "TimedPointsReward", "ItemsPerPage", "ShopDisplayTime", "ShopTextSize",
    "DbPathOverride", "DefaultKit", "GiveDinosInCryopods", "UseSoulTraps", "CryoLimitedTime",
    "UseOriginalTradeCommandWithUI", "PreventUseNoglin", "PreventUseUnconscious",
    "PreventUseHandcuffed", "PreventUseCarried",
}
KIT = {"Commands", "DefaultAmount", "Description", "Dinos", "Items", "MaxLevel", "MinLevel", "OnlyFromSpawn", "Permissions", "Price"}
SHOP = {"Amount", "Blueprint", "ClassName", "Description", "GachaResources", "Gender", "GiveToDino", "Items", "Level", "MaxLevel", "MinLevel", "Neutered", "Permissions", "PreventCryo", "Price", "SaddleBlueprint", "StryderChest", "StryderHead", "Type"}
SELL = {"Amount", "Blueprint", "Description", "Price", "Type"}
ITEM = {"Amount", "Blueprint", "ForceBlueprint", "Level", "Neutered", "Quality", "SaddleBlueprint", "StryderHead", "StryderChest", "StyderChest", "Armor", "Damage", "Durability", "Gender", "PreventCryo", "GachaResources"}
MESSAGES = set("Sender BoughtItem BoughtDino BoughtBeacon BoughtExp ReceivedPoints HavePoints NoPoints WrongId NoPermissionsKit CantBuyKit BoughtKit AvailableKits NoKits KitsLeft NoKitsLeft CantGivePoints RidingDino SentPoints GotPoints NoPlayer FoundMorePlayers BuyUsage ShopUsage KitUsage BuyKitUsage TradeUsage PointsCmd TradeCmd BuyCmd ShopCmd KitCmd BuyKitCmd SellCmd ShopSellCmd SellUsage NotEnoughItems SoldItems BadLevel KitsListPrice KitsListFormat StoreListDino StoreListItem StoreListFormat OnlyOnSpawnKit HelpCmd ShopMessage HelpMessage RefundError ShopFindCmd ShopFindUsage ShopFindNotFound ShopFindTooManyResults NoPermissionsStore InventoryIsFull ReceivedKits".split())
MONEY_KEYS = {"Price", "Points", "TotalSpent", "DefaultAmount", "Amount"}
TABLES = {
    "shop_db": {"Players": {"Id", "SteamId", "Kits", "Points", "TotalSpent"}},
    "permissions_db": {
        "Players": {"Id", "SteamId", "Groups", "TimedGroups"},
        "Groups": {"Id", "GroupName", "Permissions"},
        "Tribes": {"Id", "TribeId", "Groups", "TimedGroups"},
    },
}


class InspectionError(Exception):
    """Only a fixed reason code is safe to expose to stdout."""


def issue(report: dict, status: str, code: str, source: str = "", location: str = "") -> None:
    report["issues"].append({"status": status, "code": code, "source_ref": source, "location": location})


def strict_integer(value, maximum=MAX_INTEGER) -> bool:
    return type(value) is int and 0 <= value <= maximum


def subject(value) -> str:
    # The caller supplies the legacy namespace separately. Decimal shape never
    # establishes the provider of a native Obelisk observation.
    if type(value) is int:
        candidate = str(value)
    elif isinstance(value, str):
        candidate = value
    else:
        raise InspectionError("invalid_legacy_subject")
    if not re.fullmatch(r"[1-9][0-9]{0,19}", candidate) or int(candidate) > MAX_SUBJECT:
        raise InspectionError("invalid_legacy_subject")
    return candidate


def load_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InspectionError("duplicate_json_field")
            result[key] = value
        return result

    def constant(_):
        raise InspectionError("non_finite_json_number")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_float=Decimal, parse_constant=constant)
    except (ValueError, RecursionError, DecimalException):
        raise InspectionError("invalid_json") from None


def directory_descriptor(path: Path, *, create=False, purpose="source") -> int:
    """Walk each component without following symlinks, retaining its descriptor."""
    directory_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.absolute().parts[1:]:
            try:
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, mode=0o700, dir_fd=directory_fd)
                next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            except OSError as error:
                if error.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise InspectionError(purpose + "_symlink_rejected") from None
                raise
            os.close(directory_fd)
            directory_fd = next_fd
        result = directory_fd
        directory_fd = -1
        return result
    finally:
        if directory_fd != -1:
            os.close(directory_fd)


def source_file(path: Path, limit: int) -> tuple[Path, bytes]:
    absolute = path.absolute()
    directory_fd = directory_descriptor(absolute.parent)
    try:
        try:
            fd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise InspectionError("source_symlink_rejected") from None
            raise
    finally:
        os.close(directory_fd)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise InspectionError("source_type_or_size_rejected")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise InspectionError("source_type_or_size_rejected")
        return absolute, data
    finally:
        os.close(fd)


def unknown(report, ref, location, name, value):
    # Preserve the actual name/value privately. Arbitrary keys can themselves
    # contain account IDs or credentials, so public locations use ordinal refs.
    entry = {"source_ref": ref, "location": location, "raw_name": name, "raw_value": value}
    report["unmapped_fields"].append(entry)
    issue(report, "blocked", "unknown_field_preserved", ref, location)


def known_object(report, ref, location, value, allowed):
    if not isinstance(value, dict):
        issue(report, "blocked", "expected_object", ref, location)
        return {}
    for index, (key, child) in enumerate(value.items(), 1):
        if key not in allowed:
            unknown(report, ref, f"{location}.unknown_{index}", key, child)
        elif key in MONEY_KEYS and not strict_integer(child):
            issue(report, "blocked", "money_or_count_not_exact_nonnegative_integer", ref, f"{location}.field_{index}")
    return value


def validate_depth_and_text(report, ref, value, location="config", depth=0):
    if depth > 32:
        issue(report, "blocked", "config_depth_exceeded", ref, location)
        return
    if isinstance(value, dict):
        for index, (key, child) in enumerate(value.items(), 1):
            next_location = f"{location}.field_{index}"
            try:
                key.encode("utf-8")
            except UnicodeError:
                raise InspectionError("invalid_json_unicode") from None
            validate_depth_and_text(report, ref, child, next_location, depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_depth_and_text(report, ref, child, f"{location}.entry_{index}", depth + 1)
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise InspectionError("invalid_json_unicode") from None


def validate_boolean_fields(report, ref, value, location):
    for key in {"UseMysql", "Enabled", "StackRewards", "OnlyFromSpawn", "GiveDinosInCryopods", "UseSoulTraps", "CryoLimitedTime", "UseOriginalTradeCommandWithUI", "PreventUseNoglin", "PreventUseUnconscious", "PreventUseHandcuffed", "PreventUseCarried", "ForceBlueprint", "Neutered", "GiveToDino", "PreventCryo"} & set(value):
        if type(value[key]) is not bool:
            issue(report, "blocked", "expected_boolean", ref, location)


def inspect_delivery_shape(report, ref, entry, location):
    validate_boolean_fields(report, ref, entry, location)
    if "GachaResources" in entry:
        # Resource overrides are retained verbatim, not interpreted as native
        # item bindings. Their nested extension fields must not pass silently.
        unknown(report, ref, location + ".delivery_override", "GachaResources", entry["GachaResources"])


def inspect_config(report, ref, kind, data):
    try:
        config = load_json(data.decode("utf-8-sig"))
    except UnicodeError:
        raise InspectionError("invalid_config_utf8") from None
    source = next(s for s in report["sources"] if s["ref"] == ref)
    source["source_data"] = config
    validate_depth_and_text(report, ref, config)
    if kind == "permissions_config":
        config = known_object(report, ref, "config", config, PERMISSIONS_CONFIG)
        mode = config.get("Database")
        if mode is not None and mode not in ("sqlite", "mysql"):
            issue(report, "blocked", "unknown_permissions_database_mode", ref)
        if "UseMysql" in config and type(config["UseMysql"]) is not bool:
            issue(report, "blocked", "invalid_database_selector", ref)
        if mode in ("sqlite", "mysql") and type(config.get("UseMysql")) is bool and (mode == "mysql") != config["UseMysql"]:
            issue(report, "blocked", "conflicting_database_selectors", ref)
        issue(report, "mapping_required", "permission_namespaces_and_roles_need_review", ref)
        if mode == "mysql" or config.get("UseMysql") is True:
            issue(report, "mapping_required", "remote_database_not_connected", ref)
        source["summary"] = {"known_root_fields": len(set(config) & PERMISSIONS_CONFIG), "automatic_admin_import": False}
        return
    config = known_object(report, ref, "config", config, {"Mysql", "General", "Kits", "ShopItems", "SellItems", "Messages"})
    if "Mysql" in config:
        database = known_object(report, ref, "Mysql", config["Mysql"], MYSQL)
        if "UseMysql" in database and type(database["UseMysql"]) is not bool:
            issue(report, "blocked", "invalid_database_selector", ref)
        if database.get("UseMysql") is True:
            issue(report, "mapping_required", "remote_database_not_connected", ref)
    general = known_object(report, ref, "General", config.get("General", {}), GENERAL)
    validate_boolean_fields(report, ref, general, "General")
    if "Discord" in general:
        discord = known_object(report, ref, "General.Discord", general["Discord"], {"Enabled", "SenderName", "URL"})
        validate_boolean_fields(report, ref, discord, "General.Discord")
        issue(report, "mapping_required", "external_integration_not_activated", ref)
    if "TimedPointsReward" in general:
        reward = known_object(report, ref, "TimedPointsReward", general["TimedPointsReward"], {"Enabled", "Interval", "StackRewards", "Groups"})
        validate_boolean_fields(report, ref, reward, "TimedPointsReward")
        groups = reward.get("Groups", {})
        if not isinstance(groups, dict):
            issue(report, "blocked", "expected_reward_groups_object", ref)
        else:
            for index, entry in enumerate(groups.values(), 1):
                known_object(report, ref, f"reward_group_{index}", entry, {"Amount"})
        issue(report, "mapping_required", "rewards_require_verified_sessions_and_ledger", ref)
    counts = {}
    for section, allowed in (("Kits", KIT), ("ShopItems", SHOP), ("SellItems", SELL)):
        catalog = config.get(section, {})
        if not isinstance(catalog, dict):
            issue(report, "blocked", "expected_catalog_object", ref, section)
            continue
        counts[section] = len(catalog)
        for index, entry in enumerate(catalog.values(), 1):
            location = f"{section}.entry_{index}"
            entry = known_object(report, ref, location, entry, allowed)
            inspect_delivery_shape(report, ref, entry, location)
            if "Commands" in entry:
                issue(report, "blocked", "legacy_commands_or_admin_execution_not_imported", ref, location)
            for items in ("Items", "Dinos"):
                if items not in entry:
                    continue
                if not isinstance(entry[items], list):
                    issue(report, "blocked", "expected_items_array", ref, location)
                    continue
                for number, item in enumerate(entry[items]):
                    item_location = f"{location}.{items}.{number}"
                    item = known_object(report, ref, item_location, item, ITEM)
                    inspect_delivery_shape(report, ref, item, item_location)
            if entry:
                issue(report, "mapping_required", "catalog_permissions_and_gameplay_delivery_unmapped", ref, location)
    if "Messages" in config:
        messages = known_object(report, ref, "Messages", config["Messages"], MESSAGES)
        if any(not isinstance(value, str) for value in messages.values()):
            issue(report, "blocked", "message_not_text", ref, "Messages")
        counts["Messages"] = len(messages)
    source["summary"] = {"catalog_counts": counts, "delivery_available": False}


def csv_values(text):
    if not isinstance(text, str) or len(text) > 65536:
        raise InspectionError("invalid_permission_list")
    result = [value for value in text.split(",") if value]
    if any(value != value.strip() or "\x00" in value for value in result):
        raise InspectionError("invalid_permission_list")
    return result


def inspect_database(report, ref, kind, path, namespace, data):
    if any(os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")):
        raise InspectionError("database_sidecars_require_clean_offline_snapshot")
    if namespace != "steam":
        issue(report, "mapping_required", "explicit_legacy_steam_namespace_required", ref)
    issue(report, "mapping_required", "native_authoritative_identity_mapping_not_verified", ref)
    source = next(s for s in report["sources"] if s["ref"] == ref)
    source["proposed_records"] = []
    source["summary"] = {"table_rows": {}, "integer_totals": {}, "legacy_namespace": namespace, "authoritative_identity": False}
    # Deserialize the already-read image into private memory. SQLite never opens
    # the input path, creates a journal beside it, or assumes that it is immutable.
    # A caller still needs a coherent offline copy, not a live WAL database.
    connection = sqlite3.connect(":memory:")
    try:
        if not hasattr(connection, "deserialize"):
            raise InspectionError("sqlite_memory_snapshot_support_required")
        connection.deserialize(data)
        connection.enable_load_extension(False)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        deadline = time.monotonic() + MAX_DATABASE_SECONDS
        operations = [0]
        def progress():
            operations[0] += 1000
            return operations[0] > 1000000 or time.monotonic() > deadline
        connection.set_progress_handler(progress, 1000)
        connection.row_factory = sqlite3.Row
        expected = TABLES[kind]
        def authorize(action, first, second, database, trigger):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_PRAGMA and first == "table_xinfo" and isinstance(second, str) and second.isascii() and second.lower() in {name.lower() for name in expected}:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        connection.set_authorizer(authorize)
        # Only literal known ordinary tables are queried. Views, virtual tables,
        # unknown columns and unknown tables remain blockers, not executable input.
        objects = connection.execute("SELECT name, type, sql FROM sqlite_schema").fetchmany(101)
        if len(objects) > 100:
            raise InspectionError("database_object_limit_exceeded")
        objects = [item for item in objects if not item["name"].startswith("sqlite_")]
        available = {}
        for index, item in enumerate(objects, 1):
            canonical = next((name for name in expected if item["name"].isascii() and name.lower() == item["name"].lower()), None)
            if not canonical or item["type"] != "table" or re.search(r"\bVIRTUAL\b", item["sql"] or "", re.I):
                unknown(report, ref, f"database.object_{index}", item["name"], item["sql"])
                continue
            available[canonical] = item["name"]
        required = {"Players", "Groups"} if kind == "permissions_db" else {"Players"}
        if not required <= set(available):
            raise InspectionError("database_required_tables_missing")
        seen = set()
        defined_groups = set()
        group_references = []
        for table, actual in available.items():
            quote = '"' + actual.replace('"', '""') + '"'
            columns = list(connection.execute(f"PRAGMA table_xinfo({quote})"))
            names = {row["name"] for row in columns}
            allowed = expected[table]
            aliases = {name.lower(): name for name in names if name.isascii()}
            for number, name in enumerate(names, 1):
                if not name.isascii() or name.lower() not in {column.lower() for column in allowed}:
                    unknown(report, ref, f"{table}.column_{number}", name, {"preserved_in_source": True})
            if not {name.lower() for name in allowed} <= set(aliases):
                issue(report, "blocked", "database_required_columns_missing", ref, table)
                continue
            if any(column["hidden"] != 0 for column in columns):
                issue(report, "blocked", "generated_or_hidden_column_not_supported", ref, table)
                continue
            selected = ",".join('"' + name.replace('"', '""') + '"' for name in sorted(names))
            records = connection.execute(f"SELECT {selected} FROM {quote} LIMIT {MAX_ROWS + 1}").fetchall()
            if len(records) > MAX_ROWS:
                raise InspectionError("database_row_limit_exceeded")
            source["summary"]["table_rows"][table] = len(records)
            for index, row in enumerate(records, 1):
                if time.monotonic() > deadline:
                    raise InspectionError("database_inspection_time_budget_exceeded")
                record = {key: row[aliases[key.lower()]] for key in allowed}
                candidate = {"table": table, "row_ref": index, "source_data": dict(row), "activation_allowed": False}
                source["proposed_records"].append(candidate)
                location = f"{table}.row_{index}"
                if table == "Players":
                    try:
                        sid = subject(record["SteamId"])
                        if sid in seen:
                            issue(report, "blocked", "duplicate_legacy_account_conflict", ref, location)
                        seen.add(sid)
                        candidate["legacy_subject"] = sid
                        candidate["declared_legacy_namespace"] = namespace
                    except InspectionError as error:
                        issue(report, "blocked", str(error), ref, location)
                if kind == "shop_db":
                    for key in ("Points", "TotalSpent"):
                        value = record[key]
                        if not strict_integer(value):
                            issue(report, "blocked", "balance_not_exact_nonnegative_integer", ref, location)
                        else:
                            totals = source["summary"]["integer_totals"]
                            totals[key] = totals.get(key, 0) + value
                    try:
                        if not isinstance(record["Kits"], str) or len(record["Kits"]) > MAX_KIT_BYTES or len(record["Kits"].encode("utf-8")) > MAX_KIT_BYTES:
                            raise InspectionError("kit_json_size_limit_exceeded")
                        kits = load_json(record["Kits"])
                        validate_depth_and_text(report, ref, kits, location + ".kits")
                        if not isinstance(kits, dict):
                            raise InspectionError("invalid_kit_credits")
                        if len(kits) > MAX_KIT_ENTRIES:
                            raise InspectionError("kit_entry_limit_exceeded")
                        for number, credit in enumerate(kits.values(), 1):
                            credit = known_object(report, ref, f"{location}.kit_{number}", credit, {"Amount"})
                            if "Amount" not in credit or not strict_integer(credit["Amount"]):
                                raise InspectionError("invalid_kit_credits")
                    except InspectionError as error:
                        issue(report, "blocked", str(error), ref, location)
                    except (TypeError, UnicodeError):
                        issue(report, "blocked", "invalid_kit_credits", ref, location)
                elif table in ("Players", "Tribes"):
                    try:
                        groups = csv_values(record["Groups"])
                        group_references.append((groups, location))
                        if not isinstance(record["TimedGroups"], str):
                            raise InspectionError("invalid_timed_group_data")
                        if record["TimedGroups"]:
                            for timed in csv_values(record["TimedGroups"]):
                                parts = timed.split(";")
                                if len(parts) != 3 or any(not re.fullmatch(r"0|[1-9][0-9]{0,18}", value) or int(value) > MAX_INTEGER for value in parts[:2]) or not parts[2]:
                                    raise InspectionError("unrecognized_timed_group_format")
                                group_references.append(([parts[2]], location))
                            issue(report, "mapping_required", "timed_group_epoch_semantics_require_review", ref, location)
                    except InspectionError as error:
                        issue(report, "blocked", str(error), ref, location)
                    if table == "Tribes":
                        if not strict_integer(record["TribeId"], (1 << 31) - 1) or record["TribeId"] == 0:
                            issue(report, "blocked", "invalid_legacy_tribe_id", ref, location)
                        issue(report, "mapping_required", "tribe_cluster_namespace_and_membership_unmapped", ref, location)
                elif table == "Groups":
                    try:
                        name = record["GroupName"]
                        if not isinstance(name, str) or not name or name.strip() != name or any(mark in name for mark in (",", ";", "\x00")):
                            raise InspectionError("invalid_group_name")
                        if name.casefold() in defined_groups:
                            raise InspectionError("duplicate_group_name_conflict")
                        defined_groups.add(name.casefold())
                        permissions = csv_values(record["Permissions"])
                        if "*" in permissions or str(record["GroupName"]).casefold() in ("admins", "admin"):
                            issue(report, "mapping_required", "admin_or_wildcard_grant_requires_explicit_review", ref, location)
                    except InspectionError as error:
                        issue(report, "blocked", str(error), ref, location)
                    issue(report, "mapping_required", "legacy_permission_names_not_native_authority", ref, location)
        for groups, location in group_references:
            if any(group.casefold() not in defined_groups for group in groups):
                issue(report, "blocked", "unknown_group_reference", ref, location)
    finally:
        connection.close()


def inspect(mode: str, inputs: list[tuple[str, Path]], namespace: str | None = None) -> dict:
    report = {"schema": SCHEMA, "mode": mode, "status": "supported", "live_apply_available": False,
              "automatic_admin_import": False, "authoritative_identity": False, "source_schema_commit": SOURCE_COMMIT,
              "sources": [], "issues": [], "unmapped_fields": []}
    if not inputs:
        issue(report, "blocked", "no_sources_supplied")
    for number, (kind, requested) in enumerate(inputs, 1):
        ref = f"source_{number}"
        entry = {"ref": ref, "kind": kind, "source_path": str(requested), "source_modified": False}
        report["sources"].append(entry)
        try:
            path, data = source_file(requested, MAX_DB_BYTES if kind.endswith("_db") else MAX_CONFIG_BYTES)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["size_bytes"] = len(data)
            if kind.endswith("_db"):
                inspect_database(report, ref, kind, path, namespace, data)
            else:
                inspect_config(report, ref, kind, data)
            _, after = source_file(path, MAX_DB_BYTES if kind.endswith("_db") else MAX_CONFIG_BYTES)
            if hashlib.sha256(after).hexdigest() != entry["sha256"]:
                issue(report, "blocked", "source_changed_during_inspection", ref)
        except InspectionError as error:
            issue(report, "blocked", str(error), ref)
        except (OSError, sqlite3.Error, UnicodeError, TypeError, ValueError, OverflowError):
            issue(report, "blocked", "source_unavailable_or_invalid", ref)
        source_statuses = {item["status"] for item in report["issues"] if item["source_ref"] == ref}
        entry["status"] = "blocked" if "blocked" in source_statuses else "mapping_required" if "mapping_required" in source_statuses else "supported"
    statuses = {item["status"] for item in report["issues"]}
    report["status"] = "blocked" if "blocked" in statuses else "mapping_required" if "mapping_required" in statuses else "supported"
    return report


def public_report(report: dict) -> dict:
    private = {"source_path", "source_data", "proposed_records", "legacy_subject", "raw_name", "raw_value"}
    def redact(value):
        if isinstance(value, dict):
            return {key: ("[redacted]" if key in private else redact(child)) for key, child in value.items()}
        if isinstance(value, list):
            return [redact(child) for child in value]
        return value
    result = redact(report)
    result["redacted"] = True
    return result


def serialize(report) -> str:
    # A rejected decimal is preserved as an exact tagged string in private
    # reports, never coerced into a binary float or an accepted money amount.
    def encode(value):
        if isinstance(value, Decimal):
            return {"decimal_exact": str(value)}
        if isinstance(value, bytes):
            return {"bytes_hex": value.hex()}
        raise TypeError()
    return json.dumps(report, ensure_ascii=True, indent=2, default=encode) + "\n"


def write_private(path: Path, text: str) -> None:
    target = path.absolute()
    parent = target.parent
    directory_fd = directory_descriptor(parent, create=True, purpose="output")
    created = False
    try:
        metadata = os.fstat(directory_fd)
        if stat.S_IMODE(metadata.st_mode) != 0o700 or metadata.st_uid != os.geteuid():
            raise InspectionError("output_parent_must_be_owned_mode_0700")
        fd = os.open(target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
        created = True
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if created:
            os.unlink(target.name, dir_fd=directory_fd)
        raise
    finally:
        os.close(directory_fd)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise InspectionError("invalid_arguments")


def main(argv=None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "dry-run"))
    for option in ("permissions-config", "shop-config", "permissions-db", "shop-db"):
        parser.add_argument("--" + option, type=Path)
    parser.add_argument("--identity-namespace", choices=("steam",))
    parser.add_argument("--output", type=Path, help="new report file in an owned mode-0700 directory; never overwrites")
    parser.add_argument("--include-sensitive", action="store_true", help="requires --output; raw copied account/config data stays in that mode-0600 file")
    try:
        args = parser.parse_args(argv)
        if args.include_sensitive and not args.output:
            raise InspectionError("sensitive_output_requires_private_file")
        inputs = [(kind, getattr(args, kind)) for kind in ("permissions_config", "shop_config", "permissions_db", "shop_db") if getattr(args, kind)]
        report = inspect(args.mode, inputs, args.identity_namespace)
        rendered = serialize(report if args.include_sensitive else public_report(report))
        if args.output:
            write_private(args.output, rendered)
            # Even opt-in private reports never print account/config data to stdout.
            print(serialize({"schema": SCHEMA, "status": report["status"], "report_written": True, "sensitive_file": args.include_sensitive}), end="")
        else:
            print(rendered, end="")
        return {"supported": 0, "mapping_required": 2, "blocked": 3}[report["status"]]
    except (InspectionError, OSError) as error:
        code = str(error) if isinstance(error, InspectionError) else "output_unavailable"
        print(serialize({"schema": SCHEMA, "status": "blocked", "reason": code, "live_apply_available": False}), end="")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
