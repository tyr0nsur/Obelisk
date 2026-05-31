# SDK v1 Compatibility Contract

This document defines what `v1.0 stable` must mean for plugin authors: the complete
public SDK contract, not a runtime/core-first RC and not just proof that the internal
runtime is stable. It is a compatibility target, not a claim that the current post-RC tree
is already a complete `v1.0` SDK.

The machine-readable companion is [`public_sdk_surfaces.json`](public_sdk_surfaces.json).
That manifest's `stable_release_contract.claim_allowed` field is the explicit
machine-readable release switch for the stable SDK claim. It must remain `false` while
`v1_completion_required` is `false`; a runtime/core-first gate, internal runtime
stability, installed SDK package shape, Foundation/Plugin Hub seed, or copied
`GameplayPolicyEvent`/`ChatMessageEvent` seed cannot flip it.
`v1.0` must not be used for a runtime-only release. A stable SDK release must either
promote each important modding category through copied ABI contracts and evidence, or
explicitly exclude that category from the `v1.0` support statement.
The machine-readable `v1_sdk_completion_blockers` list records the high-demand categories
that currently prevent a complete SDK claim: player identity, permissions/admin,
command/chat response path, commands/replies, inventory/items mutation, structure
census/build policy, gameplay modules including buffs, player
services/economy/mobility/areas, and operator ingress/storage. Lifecycle ops recovery is
tracked as `obelisk.lifecycle_ops_recovery.v1`
so lifecycle/config/logging cannot be mistaken for watchdog, reload, restart, or server
recovery APIs. Gameplay/server tick callbacks are also tracked as a separate
post-v1 blocker so process-local timers are not mistaken for UE gameplay tick hooks.
Those blockers must be promoted or deliberately excluded in the release statement before
`v1_completion_required` can become true.

A pre-v1 Foundation/Plugin Hub seed can support lifecycle/config/logging,
descriptor/catalog metadata, installed-SDK consumers, and owner-token process-local
timers. That seed is useful for contributors, but pre-identity release-supported seeds are not
enough for v1 completion and are not a `v1.0` complete SDK claim.
Copied chat and gameplay-policy examples are experimental copied-data patterns only.
`GameplayPolicyEvent` and `ChatMessageEvent`, separately or together, must not be
described as a complete `v1.0` SDK, `v1.0 stable`, or sufficient to turn on
`v1_completion_required`.
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
- Legacy raw `ProcessEvent` ABI slots remain header compatibility entries only. They are
  inventoried as `obelisk.debug_raw_process_event.v1`, require explicit debug gates, and
  cannot count as promoted v1 SDK surface or completion evidence.

## Promoted Foundation

The current promoted foundation is lifecycle/config/logging, plugin metadata/init context,
owner-token callback lifetime, process-local timers, and descriptor metadata:

- `ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init`, optional `ObeliskPlugin_Shutdown`;
- `ObeliskPluginMetadata` and `ObeliskPluginInitContext`;
- `LogInfo`, `LogWarn`, and `LogError`;
- process-local `RegisterTimerWithOwnerTokenHandle` and `UnregisterTimerWithOwnerToken`;
- `DescribeResourceKind` and `DescribeGameplayPolicyEventKind`.

These are release-supported seed surfaces. They do not imply hot reload of Obelisk itself,
background ingress without shutdown proof, cluster scheduler state, gameplay timers,
resource identity, lookup, mutation, or return override.

The installed SDK package is part of this foundation contract. Creator-facing external
plugins should consume it with:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
target_link_libraries(MyPlugin PRIVATE Obelisk::obelisk_sdk)
```

The `SDK` component means the installed public header and CMake package target are
present. It is package-shape evidence only, not a `v1.0` completion marker, and does not
imply private runtime headers, vendored runtime dependencies, or any blocked gameplay
module surface.

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
sanitized logs, and global plugin config. The current core-first RC surface does not
promise a public command SDK/router, sender identity, permissions, replies, send-chat,
moderation, blocking, mutation, return override, UE lookup, or raw
UE/`FString`/params exposure.

Commands/replies is post-v1 and blocked as a combined surface. It depends on a promoted
player identity/principal contract, a promoted permission/authority model, and the
post-v1 `obelisk.command_chat_response_path.v1` command/chat response path before any
public command router or reply API can be claimed.
Identity/principal, permissions/admin, command/chat response path, and commands/replies
are an ordered v1 dependency chain: if any of those surfaces remains blocked, planning,
or post-v1, no complete v1 SDK claim is valid.
The completion checker must also reject any promoted permissions/admin,
command/chat response path, or commands/replies surface whose dependency rows are not
already promoted, and player identity promotion must name the reviewed core/reflection
evidence before it can support public permissions or command claims.
That ordering is a dependency guardrail, not a declaration that permissions/admin is the
immediate next public slice; the only post-identity candidate inside permissions/admin is
query-only fail-closed permission checks, and groups, grants, admin actions, and mutation authority remain excluded unless a future promotion gate explicitly says otherwise.

The command/chat response path is a named planning dependency only, not a promoted
surface. Until it is separately promoted, Obelisk v1 exposes no public `CallProcessEvent`
response path, raw UE pointer response API, raw `ProcessEvent` parameter response API,
raw `FString` response API, reply API, send-chat API, broadcast/notices API, or
moderation API. A future response path must use a copied append-only C ABI with a named
capability bit, nonzero owner token, owner-scoped lifecycle cleanup, privacy/redaction,
abuse/rate-limit, audit, and SDK consumer evidence.

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
Planning those missing admin snapshots must start from a reviewed non-protected complete
`obelisk.core-dump-evidence-pack.v1` plus a reviewed UFunction
`obelisk.reflection-inventory-pack.v1` that contains those two targets. An offline
`ShooterGameServer` binary, copied core, manual FName/GObjects roots, or direct
core/bin planning alone is insufficient and must not be described as public SDK,
runtime-readiness, or promotion evidence.
Player identity/principal evidence does not unlock `operator_ingress_storage`; operator
ingress/storage remains a separate post-v1 blocker until secret-safe ingress,
storage schema/migration, queue drain, audit, encoding, and lifecycle policy are promoted,
explicitly excluded, or named post-v1. The v1 release decision for
`obelisk.operator_ingress_storage.v1` has three valid outcomes: promote a reviewed
append-only copied C ABI contract with the required ingress/storage evidence and tests, or
name the surface as excluded or post-v1 in the v1 release statement. Until one of those decisions is
recorded, `v1_completion_required` must stay false and no public header, plugin callback,
storage service, RCON service, webhook client, secret manager, or cross-instance storage
API is part of the SDK.

The shortest useful route toward a complete v1 SDK is:

1. Promote the smallest copied `player_identity`/principal lifecycle contract that can
   support privacy, invalidation, and multi-instance semantics.
2. Build a fail-closed permissions/admin query layer on that principal model, initially
   limited to query-only checks.
3. Promote the command/chat response path, then promote commands/replies as a new
   owner-token copied callback/response surface, not as a parser-only extension to
   `ChatMessageEvent`.
4. While identity waits on copied core evidence, treat inventory/item copied signals as
   the higher-value side lane than structure census because they already ride copied
   `GameplayPolicyEvent` evidence. Keep that work experimental and non-completion; keep
   structure census offline planning/consume-only unless a future promotion gate accepts
   it. Promote or explicitly exclude each surface in the first v1 support statement.
5. Explicitly promote or name as excluded/post-v1 every remaining blocker ID:
   mission/transfer/dino/tribe/buff modules, player services/economy/mobility/areas,
   operator ingress/storage, and gameplay/server tick callbacks.
6. Keep gameplay/server tick callbacks separate from process-local timers unless a future
   promoted copied ABI defines cadence, budget, lifecycle, shutdown, and hitch/backpressure
   behavior.

This route keeps chat, gameplay-policy slices, descriptors, and timers as useful seed
surfaces while preventing them from being mistaken for a complete Obelisk SDK for
familiar ARK server-modding demand.

Inventory/items mutation, structure ownership/placement/build policy/no-collision,
dino/tribe/mission/transfer/buff module SDKs, RCON, database/storage services, webhooks,
economy, shops, rewards, kits, stats, player progression/engrams, homes, teleport, safe
zones, area policy, chat send/broadcast, timed notices, gameplay/server tick callbacks,
console/RCON command routing, Unicode/operator text APIs, and permissions remain outside
the current promoted scope. The machine-readable blocker entries keep those broad areas
auditable as release-statement units: structure aggregate/census, ownership/access
identity, placement/build-policy, no-collision and admin exceptions; dino
policy/cosmetics/carry restrictions, tribe identity/notices/policy, buff/status
redaction, lifecycle/stacking/invalidation, and aggregate/proximity/count/mutation
exclusions; command router, replies/send-chat, broadcast/notices, and moderation/admin
authority; inventory/item lookup, item grants/removal, kits/rewards, and player
progression/engrams; and player services, economy, mobility, area policy, and
timed-notice services. Tick callbacks are not covered by process-local timers. Economy and
mobility require promoted
identity/principal, permissions/admin, and storage/persistence; identity alone is
insufficient. If they are included in the eventual `v1.0` support statement, they must be
promoted before the release is called `v1.0`.

## v1 Release Statement Checklist

Before `stable_release_contract.claim_allowed=true`, the reviewed v1 release statement
must have exactly one outcome record for every unresolved `.v1` blocker or experimental
seed surface. Records use one of these exact forms:

```text
surface-id: promoted - ...
surface-id: excluded - ...
surface-id: post-v1 - ...
```

Duplicate records, mixed `promoted`/`excluded`/`post-v1` records for the same surface, or wording
that contradicts the chosen outcome are release blockers. A promoted record is valid only
when the manifest surface is also promoted and has surface-specific ABI evidence,
SDK-consumer evidence, lifecycle cleanup coverage, privacy/no-internals guarantees, and
the required gameplay evidence for that surface.
The manifest's `post_v1_or_excluded_surfaces` list must exactly match surfaces whose
status is `post-v1` or `excluded`; it cannot be used to classify promoted, planning,
experimental, or debug-only surfaces as release exclusions.

| Surface or demand family | Required v1 outcome | Depends on | Release-statement detail |
| --- | --- | --- | --- |
| `obelisk.player_identity.v1` | `promoted` or `excluded` | accepted admin snapshots, lifecycle anchors, privacy/invalidation, second source | Name player identity, principal, player lookup, permission principal, economy identity, and send-chat identity. |
| `obelisk.permissions_admin.v1` | `promoted`, `excluded`, or `post-v1` | promoted player identity/principal | Name permission groups, admin groups, grant/revoke, storage/persistence, operator ingress, command router, replies/send-chat, moderation, and ban/kick. |
| `obelisk.command_chat_response_path.v1` | `promoted`, `excluded`, or `post-v1` | promoted player identity/principal and permissions/admin | Name command/chat response path, public CallProcessEvent response path, raw UE pointer/ProcessEvent/FString response APIs, chat replies, send-chat, broadcast/notices, and moderation. |
| `obelisk.commands_replies.v1` | `promoted`, `excluded`, or `post-v1` | promoted player identity, permissions/admin, and command/chat response path | Name command router, console/RCON commands, player/admin commands, chat replies, send-chat, broadcast/notices, and moderation. |
| `obelisk.inventory_items_mutation.v1` | `promoted`, `excluded`, or `post-v1` | player/inventory/item identity plus rollback/privacy controls | Name Inventory SDK, Items SDK, give/remove item, kits/rewards, engrams/progression, lookup, item handles, mutation, return override, and `ResourceHandle`. |
| `obelisk.structure_census.v1` | `promoted` or `excluded` | copied structure evidence, privacy/redaction, identity policy if exposed | Name StructureEvents SDK, structure census, structure identity, lookup, build placement policy, no-collision policy, and ownership lookup. |
| `obelisk.mission_transfer_dino_tribe.v1` | `promoted` or `excluded` | each module promoted as a narrow copied ABI or explicitly left out | Name Mission SDK, Transfer SDK, Dino SDK, dino colors/cosmetics/carry rules, Tribe SDK, tribe MOTD/notices/policy, Buff/status SDK, teleport/spawn, ownership lookup, and cross-map correlation. |
| `obelisk.player_services_economy_mobility.v1` | `promoted`, `excluded`, or `post-v1` | identity, permissions/admin, storage/persistence, audit/rollback/abuse controls | Name economy, shops, rewards, kits, stats, homes, teleport, safe zones, area policy, timed notices, and cross-instance persistence. |
| `obelisk.operator_ingress_storage.v1` | `promoted`, `excluded`, or `post-v1` | secret-safe ingress, storage schema/migration, queue drain, audit, encoding, lifecycle policy | Name RCON, operator reload command API, Unicode/operator text encoding, webhooks, database/storage, secret manager, external ingress, and cross-instance storage. |
| `obelisk.gameplay_tick_callbacks.v1` | `promoted`, `excluded`, or `post-v1` | cadence, budget, threading, hitch/backpressure, lifecycle, shutdown semantics | Name server tick callbacks, UE gameplay tick callbacks, module/per-frame hooks, and gameplay timers. |
| Promoted-experimental copied seeds | `promoted`, `excluded`, or `post-v1` | full public SDK promotion evidence for each seed | Name `GameplayPolicyEvent`, `ChatMessageEvent`, plugin-local chat routing, and inventory copied signals if they remain outside v1. |
| `obelisk.lifecycle_ops_recovery.v1` | `promoted`, `excluded`, or `post-v1` | current foundation plus operator ingress for command-triggered reloads | State that lifecycle/config/logging/descriptors/timers are included, but plugin watchdogs, hot plugin reload, Obelisk hot reload, process restart, server recovery API, operator reload commands, detached-worker ingress, and restart-state recovery are excluded or post-v1 unless separately promoted. |

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

If a high-demand category is not promoted, release notes must name it explicitly as
excluded or post-v1 so plugin authors do not mistake foundation primitives for a complete
Obelisk SDK.
Umbrella names do not imply coverage: dino, tribe, buff/status, chat send/broadcast,
player progression/engrams, economy, mobility, and operator ingress/storage each need a
narrow copied C ABI surface or an explicit named exclusion.

Passing runtime/core-first RC gates, shipping the promoted foundation, or proving
pre-identity release-supported seed usefulness is insufficient for `v1.0 stable` until the
blocker list is promoted or explicitly named as excluded/post-v1 in the release
statement.
