# SDK v1 Compatibility Contract

This document defines what `v1.0` must mean for plugin authors. It is a compatibility
target, not a claim that the current post-RC tree is already a complete `v1.0` SDK.

The machine-readable companion is [`public_sdk_surfaces.json`](public_sdk_surfaces.json).
`v1.0` must not be used for a runtime-only release. A stable SDK release must either
promote each important modding category through copied ABI contracts and evidence, or
explicitly exclude that category from the `v1.0` support statement.
The machine-readable `v1_sdk_completion_blockers` list records the high-demand categories
that currently prevent a complete SDK claim: player identity, commands/replies,
permissions/admin, inventory/items mutation, structure census/build policy, gameplay
modules including buffs, player services/economy/mobility/areas, and operator
ingress/storage. Those blockers must be promoted or deliberately excluded in the release
statement before `v1_completion_required` can become true.

A pre-v1 Foundation/Plugin Hub seed can support lifecycle/config/logging,
descriptor/catalog metadata, installed-SDK consumers, and owner-token process-local
timers. That seed is useful for contributors, but it is not a `v1.0` complete SDK claim.
Copied chat and gameplay-policy examples are experimental copied-data patterns only.
Higher-level ArkApi-style categories remain outside the current promoted scope until each
has its own copied C ABI design, privacy/ownership rules, lifecycle cleanup, SDK consumer
tests, and named second-source promotion gates.

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

Lifecycle ownership is part of the promoted foundation contract: metadata string
pointers must remain valid until the plugin shared object is closed; `ObeliskApi*` and
`ObeliskPluginInitContext` borrowed strings are init-scope only. Plugins that need API
slots, config paths, instance IDs, or owner tokens during shutdown, worker threads, or
later callbacks must copy those values into plugin-owned storage during init.

## Experimental Copied Event Patterns

`GameplayPolicyEvent` is a v0.1 copied ABI surface with release-readiness evidence, but it
remains `promoted-experimental-only` in the v1 compatibility inventory until the full SDK
completion bar is met. It must be promoted, downgraded, or explicitly excluded before a
complete v1 SDK claim. It carries copied observational policy data for the named event
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

Commands/replies is post-v1 and blocked as a combined surface. It depends on a promoted
player identity/principal contract, a promoted permission/authority model, and a safe
response path for replies/send-chat before any public command router or reply API can be
claimed.

Future command/principal routing is a lifecycle and callback-ownership change, not a
parser-only extension to `ChatMessageEvent` or plugin-local routing. Any promoted design
must introduce a new copied C ABI surface with a named capability bit captured in the
plugin's init-time `ObeliskApi` table, a nonzero `plugin_owner_token`, owner-token handle
registration, owner-scoped unregister, plugin-owner cleanup on init failure or unload
before `dlclose`, callback-scope copied payloads, and principal privacy/invalidation
semantics. The runtime must reject ownerless command/principal callbacks and must not
authorize routing from process-global capability state or debug gates that were not
advertised to that plugin at init.

Player identity is planning-only. `players-identity-lifecycle-intake` and
`obelisk.players-identity-first-evidence.v1` are candidate-only,
consume-only/promote-blocked evidence lanes, not public SDK or runtime readiness. The
first-evidence gate force-redacts identity-like fields, treats `ServerKickPlayer` fields
as admin-mutation-not-public-identity, and fails closed until missing sanitized
`ServerListPlayers` and `ServerKickPlayer` snapshots, accepted lifecycle anchors,
principal privacy/invalidation semantics, and independent second-source evidence exist.

Inventory/items mutation, structure ownership/placement/build policy/no-collision,
dino/tribe/mission/transfer/buff module SDKs, RCON, database/storage services, webhooks,
economy, shops, rewards, kits, stats, homes, teleport, safe zones, area policy,
broadcast/timed notices, and permissions remain outside the current promoted scope. The
machine-readable blocker entries keep those broad areas auditable as release-statement
units: structure aggregate/census, ownership/access identity, placement/build-policy,
no-collision and admin exceptions; buff redaction, lifecycle/stacking/invalidation, and
aggregate/proximity/count/mutation exclusions; and player services, economy, mobility,
area policy, and timed-notice services. If they are included in the eventual `v1.0`
support statement, they must be promoted before the release is called `v1.0`.

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
do not satisfy a complete v1 SDK claim by themselves. A complete `v1.0` release cannot
leave `.v1` experimental contracts in that state; it must promote them to stable SDK
surfaces, move them back to planning/post-v1, or explicitly exclude them in the release
statement.

If a high-demand category is not promoted, release notes must name it as excluded or
post-v1 so plugin authors do not mistake foundation primitives for a complete ArkApi-style
modding framework.
