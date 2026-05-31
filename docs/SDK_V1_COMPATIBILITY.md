# SDK v1 Compatibility Contract

This document defines what `v1.0` must mean for plugin authors. It is a compatibility
target, not a claim that the current post-RC tree is already a complete `v1.0` SDK.

The machine-readable companion is [`public_sdk_surfaces.json`](public_sdk_surfaces.json).
`v1.0` must not be used for a runtime-only release. A stable SDK release must either
promote each important modding category through copied ABI contracts and evidence, or
explicitly exclude that category from the `v1.0` support statement.

Plugin Hub V1 production support is lifecycle/config/logging, descriptor/catalog
metadata, installed-SDK consumers, and owner-token process-local timers. Copied chat and
gameplay-policy examples are experimental copied-data patterns only. Higher-level
ArkApi-style categories remain planning or post-v1 until each has its own copied C ABI
design, privacy/ownership rules, lifecycle cleanup, SDK consumer tests, and named
second-source promotion gates.

## Global Rules

- Public SDK data is copied POD or metadata-only descriptor data.
- Plugins check `abi_version`, `struct_size`, capability bits, owner tokens, and function
  pointers before consuming appended API slots.
- Runtime handles are process-local unless a future promoted API says otherwise.
- Public surfaces must document ownership, callback lifetime, unregister behavior,
  privacy boundaries, multi-instance behavior, and release-readiness evidence.
- Raw UE pointers, raw `ProcessEvent` params, raw `FString`, FName/GObjects indices,
  ArkApi offsets, MSVC layouts, vtables, object lookup, `ResourceHandle`, mutation, and
  return override authority are not public SDK contracts.

## Promoted Foundation

The current promoted foundation is lifecycle/config/logging, plugin metadata/init context,
owner-token callback lifetime, process-local timers, and descriptor metadata:

- `ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init`, optional `ObeliskPlugin_Shutdown`;
- `ObeliskPluginMetadata` and `ObeliskPluginInitContext`;
- `LogInfo`, `LogWarn`, and `LogError`;
- process-local `RegisterTimerWithOwnerTokenHandle` and `UnregisterTimerWithOwnerToken`;
- `DescribeResourceKind` and `DescribeGameplayPolicyEventKind`.

These are production seed surfaces. They do not imply hot reload of Obelisk itself,
background ingress without shutdown proof, cluster scheduler state, gameplay timers,
resource identity, lookup, mutation, or return override.

## Experimental Copied Event Patterns

`GameplayPolicyEvent` is a promoted v0.1 copied ABI surface, but it remains
`promoted-experimental-only` in the v1 compatibility inventory until the full SDK
completion bar is met. It carries copied observational policy data for the named event
kinds in [`public_gameplay_events.json`](public_gameplay_events.json). It is not an
Inventory SDK, Items SDK, StructureEvents SDK, identity API, lookup API, mutation API, or
return-override API.

The inventory/item value that can honestly fit v1 is a copied-signal lane over
`GameplayPolicyEvent`: selected boolean policy observations such as remote-add, use,
allow-equip, repair, and use-onto-item checks. These remain post-original copied signals,
not item identity, inventory lookup, mutation, `ResourceHandle`, rollback, or grant/remove
authority.

`ChatMessageEvent` is a minimal v0.1-rc copied notification ABI. It exposes only
`abi_version`, `struct_size`, `send_mode`, `reserved0`, `flags`, process-local
`sequence`, and callback-scope copied UTF-8 `message`. It is capability-gated by
`OBELISK_API_CAPABILITY_CHAT_EVENTS` and uses owner-token handle registration/unregister.
It is not a public command router, sender identity, reply/send-chat API, moderation API,
blocking API, permission API, or raw `FString`/UE payload.

## Candidate And Planning Lanes

Plugin-local chat routing is experimental seed material only. A plugin may parse copied
`ChatMessageEvent` bytes with `principal=unknown`, plugin-owned prefixes/tables,
sanitized logs, and global plugin config. Obelisk v1 does not promise a public command
SDK/router, sender identity, permissions, replies, send-chat, moderation, blocking,
mutation, return override, UE lookup, or raw UE/`FString`/params exposure.

Player identity is planning-only. It remains blocked by missing sanitized
`ServerListPlayers` and `ServerKickPlayer` snapshots, missing accepted lifecycle anchors,
and missing privacy/invalidation semantics.

Inventory/items mutation, structure/dino/tribe/mission/transfer module SDKs, RCON,
database/storage services, webhooks, economy, homes, teleport, and permissions remain
post-v1 unless a later promotion gate explicitly moves them into the supported set.

## v1.0 Release Bar

A `v1.0` candidate must pass the normal build/test/install gates and include a reviewed
SDK compatibility statement based on `public_sdk_surfaces.json`. Any surface marked
`promoted` must have:

- ABI or installed-SDK consumer tests;
- lifecycle cleanup and unregister behavior;
- privacy and no-UE-internals guarantees;
- explicit target-set or static/offline evidence where gameplay data is involved;
- documentation that does not imply blocked categories are available.

Surfaces marked `promoted-experimental-only` can be useful RC/plugin-hub seeds, but they
do not satisfy a complete v1 SDK claim by themselves.

If a high-demand category is not promoted, release notes must name it as excluded or
post-v1 so plugin authors do not mistake foundation primitives for a complete ArkApi-style
modding framework.
