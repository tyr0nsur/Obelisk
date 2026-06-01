# Plugin Hub Package Manifest Schema

This document defines the minimum machine-readable package manifest for Plugin Hub
intake. It converts the current read-only package proposal into a JSON manifest contract
for review tooling and future package indexes.

This is not a registry implementation, not a package manager lockfile, not Obelisk SDK
v1 evidence, and not an ArkApi/AseApi compatibility format. It must not copy ArkApi,
AseApi, NextGenPlugins, or other ArkApi plugin schemas, parser behavior, constants,
offsets, control flow, ABI assumptions, or implementation patterns. Capability names and
support tiers below are Obelisk-native planning and intake vocabulary only.

Read these first:

- `docs/PLUGIN_HUB_SEED_BOUNDARY.md`
- `docs/PLUGIN_HUB_FOUNDATION_V1.md`
- `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`
- `docs/PLUGIN_HUB_PACKAGE_TEMPLATE.md`

`Foundation V1` in this context means the first reviewed Plugin Hub foundation/intake
contract revision. It does not mean Obelisk SDK v1, `v1.0 stable`, full SDK readiness, or
Plugin Hub completion.

## Manifest File

Each package candidate may include one JSON manifest named:

```text
obelisk-plugin-package.json
```

The manifest is UTF-8 JSON. Unknown top-level fields are rejected for the foundation
schema so review tooling can fail closed when a package tries to imply support outside the
declared support tier.

Required top-level fields:

- `schema_id`: must be `obelisk.plugin_hub.package_manifest`.
- `schema_version`: must be `1`.
- `package`: identity, package kind, version, declared support tier, and SDK floor.
- `artifacts`: package file inventory.
- `capabilities`: Obelisk-native capability catalog IDs and C ABI capability macros used.
- `config`: config path and safe-default posture.
- `entry_points`: exported Obelisk plugin ABI functions.
- `review_evidence`: installed-SDK build and hygiene facts.
- `review_gates`: gate IDs expected to pass before publication.
- `non_claims`: explicit false claims that tooling can check.
- `blocked_backlog`: unpromoted feature families the package needs or intentionally
  excludes.

## Minimal JSON Schema

This schema fragment is intentionally narrow. It is suitable for a first review checker,
but it is not a promise that every listed capability is release-supported.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://obelisk.local/schemas/plugin-hub/package-manifest.v1.json",
  "title": "Obelisk Plugin Hub Package Manifest",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_id",
    "schema_version",
    "package",
    "artifacts",
    "capabilities",
    "config",
    "entry_points",
    "review_evidence",
    "review_gates",
    "non_claims",
    "blocked_backlog"
  ],
  "properties": {
    "schema_id": { "const": "obelisk.plugin_hub.package_manifest" },
    "schema_version": { "const": 1 },
    "package": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "plugin_id",
        "display_name",
        "package_kind",
        "plugin_version",
        "minimum_obelisk_sdk",
        "support_tier"
      ],
      "properties": {
        "plugin_id": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9_]{2,63}$"
        },
        "display_name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 80
        },
        "package_kind": {
          "enum": [
            "runtime-plugin",
            "backlog-record"
          ]
        },
        "plugin_version": {
          "type": "string",
          "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+([-.+][A-Za-z0-9.-]+)?$"
        },
        "minimum_obelisk_sdk": {
          "type": "string",
          "pattern": "^0\\.1(\\.[0-9]+|-rc\\.[0-9]+|\\.x)?$"
        },
        "support_tier": {
          "enum": [
            "release-supported seed",
            "experimental pattern",
            "blocked backlog"
          ]
        }
      }
    },
    "artifacts": {
      "type": "object",
      "additionalProperties": false,
      "required": ["shared_object", "readme", "license"],
      "properties": {
        "shared_object": {
          "anyOf": [
            { "type": "string", "pattern": "^[A-Za-z0-9_./-]+\\.so$" },
            { "type": "null" }
          ]
        },
        "readme": { "type": "string", "pattern": "^[A-Za-z0-9_./-]*README\\.md$" },
        "license": { "type": "string", "minLength": 1 },
        "config_example_or_schema": { "type": "string" }
      }
    },
    "capabilities": {
      "type": "object",
      "additionalProperties": false,
      "required": ["catalog_ids", "api_capabilities", "target_sets"],
      "properties": {
        "catalog_ids": {
          "type": "array",
          "items": { "$ref": "#/$defs/catalog_id" },
          "uniqueItems": true
        },
        "api_capabilities": {
          "type": "array",
          "items": { "$ref": "#/$defs/api_capability" },
          "uniqueItems": true
        },
        "target_sets": {
          "type": "array",
          "items": { "$ref": "#/$defs/target_set" },
          "uniqueItems": true
        }
      }
    },
    "config": {
      "type": "object",
      "additionalProperties": false,
      "required": ["path", "safe_default"],
      "properties": {
        "path": {
          "type": "string",
          "pattern": "^\\$\\{OBELISK_CONFIG_DIR\\}/[a-z][a-z0-9_]{2,63}/config\\.json$"
        },
        "safe_default": {
          "type": "object",
          "additionalProperties": false,
          "required": ["enabled", "allow_all_instances", "instance_allowlist"],
          "properties": {
            "enabled": { "const": false },
            "allow_all_instances": { "const": false },
            "instance_allowlist": {
              "type": "array",
              "items": { "type": "string" },
              "maxItems": 0
            }
          }
        }
      }
    },
    "entry_points": {
      "type": "object",
      "additionalProperties": false,
      "required": ["required", "optional"],
      "properties": {
        "required": {
          "type": "array",
          "prefixItems": [
            { "const": "ObeliskPlugin_GetInfo" },
            { "const": "ObeliskPlugin_Init" }
          ],
          "minItems": 2,
          "maxItems": 2
        },
        "optional": {
          "type": "array",
          "items": { "const": "ObeliskPlugin_Shutdown" },
          "uniqueItems": true,
          "maxItems": 1
        }
      }
    },
    "review_evidence": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "build_system",
        "linked_target",
        "uses_private_headers",
        "uses_raw_ue_or_process_event_params",
        "uses_arkapi_or_aseapi_headers",
        "defined_symbols_reviewed"
      ],
      "properties": {
        "build_system": {
          "const": "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)"
        },
        "linked_target": { "const": "Obelisk::obelisk_sdk" },
        "uses_private_headers": { "const": false },
        "uses_raw_ue_or_process_event_params": { "const": false },
        "uses_arkapi_or_aseapi_headers": { "const": false },
        "defined_symbols_reviewed": { "type": "boolean" },
        "notes": { "type": "string" }
      }
    },
    "review_gates": {
      "type": "array",
      "items": { "$ref": "#/$defs/review_gate" },
      "uniqueItems": true,
      "minItems": 1
    },
    "non_claims": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "obelisk_sdk_v1_complete",
        "full_public_sdk",
        "production_sdk",
        "arkapi_compatible",
        "aseapi_compatible",
        "arkapi_plugin_port",
        "commands_or_replies",
        "send_chat_or_broadcast",
        "permissions_or_identity",
        "storage_or_database_service",
        "inventory_or_structure_sdk",
        "mutation_or_return_override",
        "raw_ue_pointer_access"
      ],
      "properties": {
        "obelisk_sdk_v1_complete": { "const": false },
        "full_public_sdk": { "const": false },
        "production_sdk": { "const": false },
        "arkapi_compatible": { "const": false },
        "aseapi_compatible": { "const": false },
        "arkapi_plugin_port": { "const": false },
        "commands_or_replies": { "const": false },
        "send_chat_or_broadcast": { "const": false },
        "permissions_or_identity": { "const": false },
        "storage_or_database_service": { "const": false },
        "inventory_or_structure_sdk": { "const": false },
        "mutation_or_return_override": { "const": false },
        "raw_ue_pointer_access": { "const": false }
      }
    },
    "blocked_backlog": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["catalog_id", "reason"],
        "properties": {
          "catalog_id": { "$ref": "#/$defs/catalog_id" },
          "reason": { "type": "string", "minLength": 1 }
        }
      }
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "package": {
            "properties": {
              "support_tier": { "const": "blocked backlog" }
            },
            "required": ["support_tier"]
          }
        }
      },
      "then": {
        "properties": {
          "package": {
            "properties": {
              "package_kind": { "const": "backlog-record" }
            }
          }
        }
      },
      "else": {
        "properties": {
          "package": {
            "properties": {
              "package_kind": { "const": "runtime-plugin" }
            }
          },
          "artifacts": {
            "properties": {
              "shared_object": { "type": "string", "pattern": "^[A-Za-z0-9_./-]+\\.so$" }
            }
          }
        }
      }
    }
  ],
  "$defs": {
    "catalog_id": {
      "enum": [
        "obelisk.lifecycle_config_logging.v1",
        "obelisk.descriptors.v1",
        "obelisk.process_local_timers.v1",
        "obelisk.gameplay_policy_event.v1",
        "obelisk.chat_message.v1",
        "obelisk.chat.local_routing.v1",
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.lifecycle_ops_recovery.v1",
        "obelisk.inventory_item_copied_signals.v1",
        "obelisk.inventory_items_mutation.v1",
        "obelisk.structure_census.v1",
        "obelisk.mission_transfer_dino_tribe.v1",
        "obelisk.player_services_economy_mobility.v1",
        "obelisk.operator_ingress_storage.v1"
      ]
    },
    "api_capability": {
      "enum": [
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
        "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
        "OBELISK_API_CAPABILITY_CHAT_EVENTS",
        "OBELISK_API_CAPABILITY_TIMERS"
      ]
    },
    "target_set": {
      "enum": [
        "minimal-second-source-intake",
        "structure-observer-intake",
        "item-return-only-policy-slice",
        "chat-message-intake"
      ]
    },
    "review_gate": {
      "enum": [
        "manifest.schema.v1",
        "support_tier.single.v1",
        "capability_catalog.match.v1",
        "installed_sdk.consumer.v1",
        "no_private_headers.v1",
        "no_raw_ue_or_process_event_params.v1",
        "no_arkapi_compat_claim.v1",
        "safe_disabled_config.v1",
        "entry_points.visible_only.v1",
        "abi_capability_checks.v1",
        "owner_token_cleanup.v1",
        "shutdown_idempotent.v1",
        "blocked_backlog.declared.v1"
      ]
    }
  }
}
```

## Capability Catalog

The manifest `capabilities.catalog_ids` field uses Obelisk surface IDs. A package may
list more than one ID only when every ID is allowed by the package support tier and every
used C ABI capability is checked fail-closed at runtime. Release-supported foundation IDs
are allowed as dependencies for runtime packages; experimental IDs require
`support_tier: "experimental pattern"`; blocked IDs require
`support_tier: "blocked backlog"`.

| Catalog ID | Manifest tier | API capability macros | Meaning | Must not imply |
| --- | --- | --- | --- | --- |
| `obelisk.lifecycle_config_logging.v1` | `release-supported seed` | none | Plugin entry points, config context, logging, metadata, and shutdown hygiene. | Hot reload, watchdogs, recovery APIs, operator reload commands, or cross-process state. |
| `obelisk.descriptors.v1` | `release-supported seed` | `OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS`, `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS` | Metadata-only resource and policy event descriptors. | Resource identity, object lookup, persistent handles, mutation, or return override. |
| `obelisk.process_local_timers.v1` | `release-supported seed` | `OBELISK_API_CAPABILITY_TIMERS` | Owner-token process-local timers for plugin-owned work. | UE gameplay timers, persistent timer ids, cluster scheduling, command routing, or permissions. |
| `obelisk.chat_message.v1` | `experimental pattern` | `OBELISK_API_CAPABILITY_CHAT_EVENTS` | Copied callback-scope chat message observation for plugin-local parsing. | Public command SDK/router, sender identity, permissions, replies, send-chat, moderation, blocking, or mutation. |
| `obelisk.chat.local_routing.v1` | `experimental pattern` | `OBELISK_API_CAPABILITY_CHAT_EVENTS` | Plugin-local text routing over copied chat data. | Obelisk command registration, cross-plugin dispatch, sender identity, permissions, replies, send-chat, moderation, or authoritative command lifecycle. |
| `obelisk.gameplay_policy_event.v1` | `experimental pattern` | `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS` | Copied/redacted `GameplayPolicyEvent` observation for promoted target sets. | Inventory SDK, Items SDK, StructureEvents SDK, identity, lookup, mutation, return override, `ResourceHandle`, or raw UE pointers. |
| `obelisk.inventory_item_copied_signals.v1` | `experimental pattern` | `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS` | Inventory/item copied policy signals only through `GameplayPolicyEvent`. | Inventory SDK, Items SDK, item identity, item lookup, give/remove, mutation, rollback, or return override. |
| `obelisk.player_identity.v1` | `blocked backlog` | none | Future identity/principal lane. | Current player identity, permissions, moderation, economy identity, or send-chat identity support. |
| `obelisk.permissions_admin.v1` | `blocked backlog` | none | Future permissions/admin lane after identity. | Current groups, grants, admin actions, command authorization, or permission storage support. |
| `obelisk.lifecycle_ops_recovery.v1` | `blocked backlog` | none | Future reload, recovery, watchdog, and operator lifecycle lane. | Current hot reload, crash recovery, process restart, detached-worker ingress, or reload command APIs. |
| `obelisk.inventory_items_mutation.v1` | `blocked backlog` | none | Future inventory/items identity and mutation lane. | Current Inventory SDK, Items SDK, item handles, give/remove item, kits/rewards, engrams, mutation, or return override. |
| `obelisk.structure_census.v1` | `blocked backlog` | none | Future structure census, identity, ownership, and build-policy lane. | Current StructureEvents SDK, structure identity, ownership lookup, placement denial, no-collision control, mutation, or return override. |
| `obelisk.mission_transfer_dino_tribe.v1` | `blocked backlog` | none | Future mission, transfer, dino, tribe, and buff/status lanes. | Current Mission SDK, Transfer SDK, Dino SDK, Tribe SDK, Buff SDK, teleport/spawn APIs, ownership lookup, or cross-map correlation. |
| `obelisk.player_services_economy_mobility.v1` | `blocked backlog` | none | Future economy, shops, rewards, kits, homes, teleport, safe-zone, and area-policy umbrella. | Current economy API, shop API, rewards API, kits API, homes API, teleport API, timed notices, or cross-instance persistence. |
| `obelisk.operator_ingress_storage.v1` | `blocked backlog` | none | Future RCON/operator ingress, external text, storage, database, webhook, and secret-management lane. | Current RCON, webhook, database/storage service, secret manager, external ingress, or cross-instance storage API. |

If a package declares a blocked catalog ID, its support tier must be `blocked backlog`.
That package is a design, evidence, or guardrail package only; it is not a public Plugin
Hub module. A `blocked backlog` manifest uses `package_kind: "backlog-record"` and may use
`artifacts.shared_object: null` because no runtime module is being accepted.

## Review Gates

Review tooling should treat the manifest as a fail-closed intake document. A package is
not accepted just because the JSON validates.

Minimum gates:

- `manifest.schema.v1`: the file validates against the schema above and has no unknown
  top-level fields.
- `support_tier.single.v1`: exactly one support tier is declared in the manifest and
  README, and the values match.
- `capability_catalog.match.v1`: every `catalog_id`, `api_capability`, and `target_set`
  is allowed by the declared support tier.
- `installed_sdk.consumer.v1`: the package builds with
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and links only
  `Obelisk::obelisk_sdk`.
- `no_private_headers.v1`: source and compile commands do not include private Obelisk
  headers or repository-local runtime plugin wiring.
- `no_raw_ue_or_process_event_params.v1`: source does not use raw UE types, raw
  `ProcessEvent` params, `GetNativePointerField`, `NativeCall`, `ResourceHandle`, or
  raw game memory as a Plugin Hub dependency.
- `no_arkapi_compat_claim.v1`: manifest and README do not claim ArkApi/AseApi
  compatibility, ArkApi plugin portability, source parity, behavior parity, Windows/MSVC
  ABI portability, or copied ArkApi implementation semantics.
- `safe_disabled_config.v1`: config defaults are disabled, not all-instance active, and
  use an empty instance allowlist.
- `entry_points.visible_only.v1`: defined dynamic symbols are reviewed and limited to the
  Obelisk plugin entry points needed by the declared tier.
- `abi_capability_checks.v1`: runtime code checks `abi_version`, `struct_size`, capability
  bits, non-null function pointers, and callback-scope data lifetimes before use.
- `owner_token_cleanup.v1`: callback and timer registrations use nonzero owner tokens,
  process-local handles, same-owner unregister, and cleanup on partial init failure.
- `shutdown_idempotent.v1`: shutdown is exported when callbacks, timers, retained
  descriptor state, worker state, or partial init cleanup are possible, and shutdown is
  idempotent.
- `blocked_backlog.declared.v1`: any feature depending on identity, permissions,
  commands, replies, send-chat, storage, mutation, inventory, structures, operator
  ingress, cross-instance state, or raw UE access is listed in `blocked_backlog` or the
  package is rejected.

Release-supported packages may use only `release-supported seed` catalog IDs.
Experimental packages may combine `experimental pattern` IDs with release-supported
foundation IDs when needed for metadata, config, logging, or timers; they must also
include the relevant release-readiness target set and avoid production module wording.
Blocked packages may include blocked IDs, but they must not ship as runtime modules.

## Non-Claims

The `non_claims` object is required so package indexes and review tools can reject broad
claims mechanically. Every value must be `false`.

These false values are part of the package contract:

- no Obelisk SDK v1 completion claim;
- no full public SDK or production SDK claim;
- no ArkApi/AseApi compatibility or direct ArkApi plugin port claim;
- no commands, replies, send-chat, broadcast, permissions, identity, moderation, storage,
  database, webhook, inventory, structure, mutation, return override, or raw UE pointer
  support outside the declared tier.

Human README wording must match the manifest. A package cannot override these
non-claims with marketing text, examples, screenshots, or compatibility notes.

## Blocked Backlog

`blocked_backlog` is required even when it is an empty array. Use it to make deferred
needs explicit instead of implying that a timer, descriptor, passive chat parser, or
copied policy audit unlocks a higher-level module.

Examples of features that must be routed to blocked backlog:

- commands, command routers, command replies, send-chat, broadcast, moderation, and
  command authorization;
- player identity, principals, player lookup, tribe identity, dino identity, item
  identity, structure identity, ownership lookup, and persistent handles;
- permissions/admin checks, groups, grants, admin actions, RCON/operator ingress, reload
  commands, and operator text services;
- economy, shops, kits, rewards, stats, homes, teleport, safe zones, area policy, timed
  notices that need chat/broadcast, and cross-instance state;
- storage/database/webhook services, secret management, schema migrations, and
  cross-instance persistence;
- inventory/item grant, remove, mutate, rollback, engram/progression, and return
  override behavior;
- structure census, placement denial, no-collision control, pincode/value exposure,
  mutation, and enforcement;
- missions, transfers, buffs/status, dino cosmetics/carry/spawn, tribe MOTD/notices, and
  cross-map correlation.

Demand from ArkApi/AseApi names or local NextGenPlugins inventories may justify why a
blocked feature appears in backlog, but it cannot change the support tier and cannot be
used as compatibility or implementation evidence.

## Minimal Examples

Release-supported descriptor package:

```json
{
  "schema_id": "obelisk.plugin_hub.package_manifest",
  "schema_version": 1,
  "package": {
    "plugin_id": "descriptor_catalog",
    "display_name": "Descriptor Catalog",
    "package_kind": "runtime-plugin",
    "plugin_version": "0.1.0",
    "minimum_obelisk_sdk": "0.1.x",
    "support_tier": "release-supported seed"
  },
  "artifacts": {
    "shared_object": "libdescriptor_catalog.so",
    "readme": "README.md",
    "license": "LICENSE",
    "config_example_or_schema": "config.example.json"
  },
  "capabilities": {
    "catalog_ids": ["obelisk.descriptors.v1"],
    "api_capabilities": [
      "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
      "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS"
    ],
    "target_sets": []
  },
  "config": {
    "path": "${OBELISK_CONFIG_DIR}/descriptor_catalog/config.json",
    "safe_default": {
      "enabled": false,
      "allow_all_instances": false,
      "instance_allowlist": []
    }
  },
  "entry_points": {
    "required": ["ObeliskPlugin_GetInfo", "ObeliskPlugin_Init"],
    "optional": ["ObeliskPlugin_Shutdown"]
  },
  "review_evidence": {
    "build_system": "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
    "linked_target": "Obelisk::obelisk_sdk",
    "uses_private_headers": false,
    "uses_raw_ue_or_process_event_params": false,
    "uses_arkapi_or_aseapi_headers": false,
    "defined_symbols_reviewed": true
  },
  "review_gates": [
    "manifest.schema.v1",
    "support_tier.single.v1",
    "capability_catalog.match.v1",
    "installed_sdk.consumer.v1",
    "no_private_headers.v1",
    "no_raw_ue_or_process_event_params.v1",
    "no_arkapi_compat_claim.v1",
    "safe_disabled_config.v1",
    "entry_points.visible_only.v1",
    "abi_capability_checks.v1",
    "shutdown_idempotent.v1",
    "blocked_backlog.declared.v1"
  ],
  "non_claims": {
    "obelisk_sdk_v1_complete": false,
    "full_public_sdk": false,
    "production_sdk": false,
    "arkapi_compatible": false,
    "aseapi_compatible": false,
    "arkapi_plugin_port": false,
    "commands_or_replies": false,
    "send_chat_or_broadcast": false,
    "permissions_or_identity": false,
    "storage_or_database_service": false,
    "inventory_or_structure_sdk": false,
    "mutation_or_return_override": false,
    "raw_ue_pointer_access": false
  },
  "blocked_backlog": []
}
```

Blocked backlog record:

```json
{
  "schema_id": "obelisk.plugin_hub.package_manifest",
  "schema_version": 1,
  "package": {
    "plugin_id": "economy_design",
    "display_name": "Economy Design",
    "package_kind": "backlog-record",
    "plugin_version": "0.1.0",
    "minimum_obelisk_sdk": "0.1.x",
    "support_tier": "blocked backlog"
  },
  "artifacts": {
    "shared_object": null,
    "readme": "README.md",
    "license": "LICENSE"
  },
  "capabilities": {
    "catalog_ids": ["obelisk.player_services_economy_mobility.v1"],
    "api_capabilities": [],
    "target_sets": []
  },
  "config": {
    "path": "${OBELISK_CONFIG_DIR}/economy_design/config.json",
    "safe_default": {
      "enabled": false,
      "allow_all_instances": false,
      "instance_allowlist": []
    }
  },
  "entry_points": {
    "required": ["ObeliskPlugin_GetInfo", "ObeliskPlugin_Init"],
    "optional": []
  },
  "review_evidence": {
    "build_system": "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
    "linked_target": "Obelisk::obelisk_sdk",
    "uses_private_headers": false,
    "uses_raw_ue_or_process_event_params": false,
    "uses_arkapi_or_aseapi_headers": false,
    "defined_symbols_reviewed": false,
    "notes": "Design-only backlog package; not a public runtime module."
  },
  "review_gates": [
    "manifest.schema.v1",
    "support_tier.single.v1",
    "capability_catalog.match.v1",
    "no_arkapi_compat_claim.v1",
    "blocked_backlog.declared.v1"
  ],
  "non_claims": {
    "obelisk_sdk_v1_complete": false,
    "full_public_sdk": false,
    "production_sdk": false,
    "arkapi_compatible": false,
    "aseapi_compatible": false,
    "arkapi_plugin_port": false,
    "commands_or_replies": false,
    "send_chat_or_broadcast": false,
    "permissions_or_identity": false,
    "storage_or_database_service": false,
    "inventory_or_structure_sdk": false,
    "mutation_or_return_override": false,
    "raw_ue_pointer_access": false
  },
  "blocked_backlog": [
    {
      "catalog_id": "obelisk.player_identity.v1",
      "reason": "Economy requires promoted player identity/principal before balances or rewards can be attributed."
    },
    {
      "catalog_id": "obelisk.operator_ingress_storage.v1",
      "reason": "Economy requires a promoted persistence/storage contract before package publication."
    }
  ]
}
```
