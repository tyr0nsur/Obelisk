# SDK v1 Compatibility Contract

This document defines what `v1.0 stable` must mean for plugin authors: the complete
public SDK contract, not a runtime/core-first RC and not just proof that the internal
runtime is stable. It is a compatibility target, not a claim that the current post-RC tree
is already a complete `v1.0` SDK.

The machine-readable companion is [`public_sdk_surfaces.json`](public_sdk_surfaces.json).
That manifest's `stable_release_contract.claim_allowed` field is the explicit
machine-readable release switch for the stable SDK claim. It must remain `false` while
`v1_completion_required` is `false`; a runtime/core-first gate, internal runtime
stability, installed SDK package shape, foundation examples, Plugin Hub packaging, or any
promoted-experimental copied-data surface cannot flip it.
The completion checker reports that raw switch as
`stable_release_contract_claim_allowed` and reserves `stable_claim_allowed` for the final
computed gate result after all blockers are applied.
`v1.0` must not be used for a runtime-only release. The P0 dependency chain
(`player_identity`, `permissions_admin`, `command_chat_response_path`,
`commands_replies`) must be promoted through copied ABI contracts and evidence before any
complete SDK claim. Non-chain high-demand categories may be promoted or explicitly named
as excluded/post-v1 in a scoped release statement, but that accounting does not complete
the excluded capability.
The machine-readable `v1_sdk_completion_blockers` list records the high-demand categories
that currently prevent a complete SDK claim: player identity, permissions/admin,
command/chat response path, commands/replies, inventory/items mutation, structure
census/build policy, object identity/ResourceHandle, lifecycle ops recovery, gameplay
modules including buffs, mission/transfer/dino/tribe/buff-status, player
services/economy/mobility/areas, operator ingress/storage, and gameplay/server tick
callbacks. Lifecycle ops recovery is tracked as `obelisk.lifecycle_ops_recovery.v1`
so lifecycle/config/logging cannot be mistaken for watchdog, reload, restart, or server
recovery APIs. Object identity/ResourceHandle is tracked separately so copied category
metadata cannot be mistaken for lookup handles, persistent handles, or post-callback
object correlation. Gameplay/server tick callbacks are also tracked as a separate v1
completion blocker so process-local timers are not mistaken for UE gameplay tick hooks.
The P0 chain must be promoted before `v1_completion_required` can become true; non-chain
blockers must be promoted or deliberately excluded/post-v1 in the release statement before
they stop blocking scoped support-statement accounting.

A pre-v1 installed-SDK foundation example can support lifecycle/config/logging,
descriptor/catalog metadata, installed-SDK consumers, and owner-token process-local
timers. Those examples are useful for contributors, but Plugin Hub seed/package
publication remains post-SDK-complete and pre-identity installed-SDK foundation
usefulness is insufficient for v1 completion or a `v1.0` complete SDK claim.
Plugin Hub remains post-SDK-complete planning: no seed/package publication, intake
prioritization, production module availability, or support-tier activation may be
inferred from v0.1 RC surfaces, installed SDK package shape, foundation examples, or
promoted-experimental copied-data seeds.
Copied chat and gameplay-policy examples are experimental copied-data patterns only.
`GameplayPolicyEvent` and `ChatMessageEvent`, separately or together, must not be
described as a complete `v1.0` SDK, `v1.0 stable`, or sufficient to turn on
`v1_completion_required`.
Higher-level ArkApi-style categories remain outside the current promoted scope until each
has its own copied C ABI design, privacy/ownership rules, lifecycle cleanup, SDK consumer
tests, and named second-source promotion gates.
No Foundation seed, Plugin Hub seed, descriptor/timer example, installed SDK package shape, or
copied event example is an ArkApi/AseApi/ArkServerApi compatibility layer, API parity
claim, portable plugin path, or evidence that ArkApi plugin families can be ported.
This does not prevent Obelisk from using familiar capability grouping as demand
vocabulary, provided no source/API/ABI/behavior compatibility, porting guidance,
workflow-shape guidance, or AseApi-derived ergonomics are claimed.

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

These are release-supported foundation surfaces for the SDK package, not Plugin Hub
priority. They do not imply hot reload of Obelisk itself, background ingress without
shutdown proof, cluster scheduler state, gameplay timers, resource identity, lookup,
mutation, or return override.

The installed SDK package is part of this foundation contract. Creator-facing external
plugins should consume it with:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
target_link_libraries(MyPlugin PRIVATE Obelisk::obelisk_sdk)
```

The `SDK` component means only the installed public header and CMake package target are
present:

```text
include/obelisk/ObeliskApi.h
lib/cmake/Obelisk/ObeliskConfig.cmake
lib/cmake/Obelisk/ObeliskConfigVersion.cmake
lib/cmake/Obelisk/ObeliskTargets.cmake
```

That file set is package-shape evidence only, not a `v1.0` completion marker, and does
not imply private runtime headers, vendored runtime dependencies, Plugin Hub package
publication, or any blocked gameplay module surface.
The installed CMake package exports explicit non-claim metadata with package-shape status
and false Plugin Hub publication, v1 completion, public module SDK coverage, and
production stable SDK claim variables. Consumers must not reinterpret `Obelisk_SDK_FOUND`,
the package version, or example builds as broader readiness evidence.

Lifecycle ownership is part of the promoted foundation contract: metadata string
pointers must remain valid until the plugin shared object is closed; `ObeliskApi*` and
`ObeliskPluginInitContext` borrowed strings are init-scope only. Plugins that need API
slots, config paths, instance IDs, or owner tokens during shutdown, worker threads, or
later callbacks must copy those values into plugin-owned storage during init.

## Experimental Copied Event Patterns

`GameplayPolicyEvent` is a v0.1 copied ABI surface with release-readiness evidence, but it
remains `promoted-experimental-only` in the v1 compatibility inventory until the v1
completion bar is met. It must be promoted, downgraded to planning/post-v1, or explicitly excluded
before a complete v1 SDK claim. It carries copied observational policy data for the named
event kinds in [`public_gameplay_events.json`](public_gameplay_events.json). It is not an
Inventory SDK, Items SDK, StructureEvents SDK, identity API, lookup API, mutation API, or
return-override API.

The inventory/item value that can honestly fit v1 is a copied-signal lane over
`GameplayPolicyEvent`: selected boolean policy observations such as remote-add, use,
allow-equip, repair, and use-onto-item checks. These remain post-original copied signals,
not item identity, inventory lookup, mutation, `ResourceHandle`, rollback, or grant/remove
authority.
Inventory-named `GameplayPolicyEvent` kinds are promoted only as copied event kinds inside
the gameplay-policy surface; they are not an Inventory SDK or Items SDK and do not expose
inventory/item identity, lookup, mutation, item handles, grant/remove, rollback, or
`ResourceHandle`.
Controller-side inventory-action observer hygiene is separate from those promoted
inventory-named `GameplayPolicyEvent` kinds. `scripts/check_inventory_action_redacted_observer_gate.py`
is an offline candidate-only checker for the `inventory-action-compact-intake` target set
and a future redacted observer marker. It must continue to report no runtime readiness,
no public SDK readiness, no dispatch readiness, and no promotion readiness. It does not
add a runtime observer, public Inventory/Items SDK, item or inventory identity, lookup,
mutation, return override, `ResourceHandle`, public callback, or public ABI, and it
cannot be used as `v1.0` completion evidence.

`ChatMessageEvent` is a minimal v0.1-rc copied notification ABI. It exposes only
`abi_version`, `struct_size`, `send_mode`, `reserved0`, `flags`, process-local
`sequence`, and callback-scope copied UTF-8 `message`. It is capability-gated by
`OBELISK_API_CAPABILITY_CHAT_EVENTS` and uses owner-token handle registration/unregister.
It is not a public command router, sender identity, reply/send-chat API, moderation API,
blocking API, permission API, or raw `FString`/UE payload.

## Candidate And Planning Lanes

Plugin-local chat routing is experimental copied-pattern material only. A plugin may parse copied
`ChatMessageEvent` bytes with `principal=unknown`, plugin-owned prefixes/tables,
sanitized logs, and global plugin config. The current core-first RC surface does not
promise a public command SDK/router, sender identity, permissions, replies, send-chat,
moderation, blocking, mutation, return override, UE lookup, or raw
UE/`FString`/params exposure.

Commands/replies is a blocked v1 completion surface. It depends on a promoted
player identity/principal contract, a promoted permission/authority model, and the
blocked `obelisk.command_chat_response_path.v1` planning dependency before any
public command router or reply API can be claimed.
The pre-ABI decision checklist for the future commands/replies surface is
[`commands_replies_public_contract_decisions.json`](commands_replies_public_contract_decisions.json).
`scripts/check_commands_replies_public_readiness.py` is the matching local readiness
guardrail; on the current tree it must remain a blocked/post-v1 report, not promotion
or public SDK evidence.
It is a blocking checklist only: passive `ChatMessageEvent` parsing, plugin-local
command parser scaffolds, static thunk orientation, raw `ProcessEvent` callbacks,
legacy `CallProcessEvent` debug access, and ArkApi/AseApi compatibility names are not
sufficient command/reply evidence and cannot be cited as public response evidence.
Identity/principal, permissions/admin, command/chat response path, and commands/replies
are an ordered v1 dependency chain: if any of those surfaces remains blocked, planning,
or post-v1, no complete v1 SDK claim is valid.
The completion checker must also reject any promoted permissions/admin,
command/chat response path, or commands/replies surface whose dependency rows are not
already promoted, and player identity promotion must name the reviewed core/reflection
evidence before it can support public permissions or command claims.
Promoted command/chat response and commands/replies evidence must also name the promoted
identity/principal and permissions prerequisites plus copied response/command ABI,
owner-scoped lifecycle, privacy/redaction, abuse/rate-limit, audit, and command
lifecycle boundaries before those rows can support v1 release-claim accounting.
That ordering is a dependency guardrail, not a declaration that permissions/admin is the
immediate next public slice; the only post-identity candidate inside permissions/admin is
query-only fail-closed permission checks over copied principals. Before player identity
is promoted, permissions/admin has no public header symbols, callbacks, command/reply
implication, or public cache ABI. After identity promotion, any permission `allow` must
carry policy source, authority generation, and `policy_epoch` provenance; missing or
stale provenance returns deny or unknown, never allow. Groups, grants, admin actions,
moderation actions, mutation authority, command/chat response paths, replies/send-chat,
storage/persistence, and operator ingress remain excluded unless a future promotion gate
explicitly says otherwise. The pre-ABI decision checklist for this future surface is
[`permissions_admin_public_contract_decisions.json`](permissions_admin_public_contract_decisions.json).
groups, grants, admin actions, and mutation authority remain excluded from the
permissions/admin candidate.

The command/chat response path is a named planning dependency only, not a promoted
surface. Until it is separately promoted, Obelisk v1 exposes no public `CallProcessEvent`
response path, raw UE pointer response API, raw `ProcessEvent` parameter response API,
raw `FString` response API, reply API, send-chat API, broadcast/notices API, or
moderation API. A future response path must use a copied append-only C ABI with a named
capability bit, nonzero owner token, owner-scoped lifecycle cleanup, privacy/redaction,
abuse/rate-limit, audit, and SDK consumer evidence.
The pre-ABI decision checklist for that future path is
[`command_chat_response_public_contract_decisions.json`](command_chat_response_public_contract_decisions.json).
It is a blocking checklist only: static thunk orientation, passive `ChatMessageEvent`
parsing, candidate vtable slots, raw `ProcessEvent` callbacks, and the legacy
`CallProcessEvent` debug gate are not sufficient response-path evidence.
The public-readiness checker also scans `include/obelisk/ObeliskApi.h`; capability bits,
ABI versions, register/unregister APIs, reply/send/broadcast/notice APIs, or public
`CallProcessEvent` response symbols in that header are blockers while the surface remains
planning-only.

Future command/principal routing is a lifecycle and callback-ownership change, not a
parser-only extension to `ChatMessageEvent` or plugin-local routing. Any promoted design
must introduce a new copied C ABI surface with a named capability bit captured in the
plugin's init-time `ObeliskApi` table, a nonzero `plugin_owner_token`, owner-token handle
registration, owner-scoped unregister, plugin-owner cleanup on init failure or unload
before `dlclose`, callback-scope copied payloads, and principal privacy/invalidation
semantics. The runtime must reject ownerless command/principal callbacks and must not
authorize routing from process-global capability state or debug gates that were not
advertised to that plugin at init.
Familiar migration vocabulary is allowed only as planning language. Terms such as chat
command, console command, admin-like command, reply request, and permission action do not
claim ArkApi/AseApi parser compatibility, dispatch ordering compatibility, return
semantics compatibility, direct plugin portability, copied parser/control flow, or ABI
compatibility.
The planning bridge is tracked by
[`command_principal_authz_response_bridge_decisions.json`](command_principal_authz_response_bridge_decisions.json)
and its checker; it is a fail-closed vocabulary/header-drift guardrail only, not a public
ABI or promoted SDK surface.
`scripts/check_command_permission_route_gate.py --json` is the aggregate offline posture
check for this route. A passing report means the route remains internally consistent for
planning only; it is not release evidence, public ABI readiness, runtime readiness,
command router readiness, reply/send-chat readiness, or v1 completion evidence.

Player identity is planning-only. `players-identity-lifecycle-intake` and
`obelisk.players-identity-first-evidence.v1` are candidate-only,
consume-only/promote-blocked evidence lanes, not public SDK or runtime readiness. The
current lane requires a reviewed non-protected complete
`obelisk.core-dump-evidence-pack.v1`, a reviewed UFunction
`obelisk.reflection-inventory-pack.v1`, candidate fixtures, and accepted distinct
second-source layout coverage for the 12-target intake, including
`ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer`. `ServerListPlayers` and `ServerKickPlayer`
snapshots are evidence inputs only. The first-evidence gate force-redacts
identity-like fields and treats `ServerKickPlayer` fields as
admin-mutation-not-public-identity. It still fails closed until approved runtime principal
lifecycle evidence, accepted lifecycle ordering, principal privacy/invalidation semantics,
and cross-instance scope behavior exist. An offline `ShooterGameServer` binary, copied
core, manual FName/GObjects roots, or direct core/bin planning alone is insufficient.
Candidate fixtures or second-source layout acceptance alone are also insufficient and
must not be described as public SDK, runtime-readiness, or promotion evidence. Source-bound
lifecycle anchors and independent second-source layout evidence are accepted as
candidate-only planning inputs; remaining promotion blockers include approved runtime
principal lifecycle evidence, lifecycle semantics/privacy/scope review, public ABI/SDK
consumer coverage, and owner/lifecycle cleanup gates.
The future `obelisk.players-identity-principal-invalidation-policy.v1` artifact is a
candidate-only policy input; it does not promote player identity/principal,
permissions/admin, command response paths, commands/replies, runtime readiness, or v1 SDK
completion.
Player identity/principal evidence does not unlock `operator_ingress_storage`; operator
ingress/storage remains a separate v1 completion blocker until secret-safe ingress,
storage schema/migration, queue drain, audit, encoding, and lifecycle policy are promoted,
explicitly excluded, or named post-v1. The v1 release decision for
`obelisk.operator_ingress_storage.v1` has three valid outcomes: promote a reviewed
append-only copied C ABI contract with the required ingress/storage evidence and tests, or
name the surface as excluded or post-v1 in the v1 release statement. Until one of those decisions is
recorded, `v1_completion_required` must stay false and no public header, plugin callback,
storage service, RCON service, webhook client, secret manager, or cross-instance storage
API is part of the SDK. `scripts/check_operator_ingress_storage_offline_contract.py`
validates the offline planning contract only and must not be cited as public ABI,
runtime readiness, promotion readiness, or v1 completion evidence.
Any acceptable runtime principal lifecycle evidence must come from a copied offline
workspace log plus a checked operational window manifest. Live/protected source paths,
private identity terms, UE internals, public capability claims, and readiness claims keep
the evidence out of the promotion path.

The shortest useful route toward a complete v1 SDK is:

1. Promote the smallest copied `player_identity`/principal lifecycle contract that can
   support privacy, invalidation, and multi-instance semantics.
2. Build a fail-closed permissions/admin query layer on that principal model, initially
   limited to query-only checks with no public cache ABI, no command/reply implication,
   and no admin mutation.
3. Promote the command/chat response path, then promote commands/replies as a new
   owner-token copied callback/response surface, not as a parser-only extension to
   `ChatMessageEvent`.
4. While identity waits on approved copied runtime principal lifecycle evidence, treat
   inventory/item copied signals as the higher-value side lane than structure census
   because they already ride copied `GameplayPolicyEvent` evidence. Keep that work
   experimental and non-completion; keep structure census offline planning/consume-only
   unless a future promotion gate accepts it. Promote or explicitly exclude each surface
   in the first v1 support statement.
5. Explicitly promote or name as excluded/post-v1 every remaining blocker ID. The
   `obelisk.mission_transfer_dino_tribe.v1` umbrella is split for accounting into
   mission, transfer, dino policy, tribe policy, and buff/status leaf decisions; the v1
   release outcome must name each leaf as promoted through its own narrow copied ABI or
   explicitly excluded by name. This split does not create new public surfaces or resolve
   the umbrella blocker; `obelisk.mission_transfer_dino_tribe.v1` remains unresolved until
   promoted or explicitly excluded in a reviewed v1 release statement. Player
   services/economy/mobility/areas, operator ingress/storage, and gameplay/server tick
   callbacks remain separate blockers.
   `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` is an accounting
   guardrail for that leaf outcome split, not a promotion checker.
6. Keep gameplay/server tick callbacks separate from process-local timers unless a future
   promoted copied ABI defines cadence, budget, lifecycle, shutdown, and hitch/backpressure
   behavior.

This route keeps chat, gameplay-policy slices, descriptors, and timers as useful copied
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
copied surface. Records use one of these exact forms:

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
experimental, or debug-only surfaces as release exclusions. The ordered P0 dependency
chain (`player_identity`, `permissions_admin`, `command_chat_response_path`,
`commands_replies`) is the complete-SDK spine and is tracked separately as
`v1_required_dependency_chain`; excluded/post-v1 is not a valid complete-SDK outcome for
that chain.
Post-v1 or excluded records are support-statement accounting only. They do not authorize
complete, full, production, or stable SDK wording unless
`scripts/check_public_sdk_v1_completion.py --json` reports that the stable claim is
allowed.
Excluded/post-v1 outcomes permit only scoped non-complete release wording; they never
contribute percentage toward a complete, full, production, or stable SDK claim.
The checker's `v1_sdk_blocker_outcomes` rows are an accounting ledger for prioritizing
the 12 blocker outcomes: each row reports the manifest outcome, release-statement
outcome, exclusion-contract satisfaction, and next action. Those rows are not a release
approval and must not be cited as evidence that a surface is included in v1.

| Surface or demand family | Required v1 outcome | Depends on | Release-statement detail |
| --- | --- | --- | --- |
| `obelisk.player_identity.v1` | `promoted` | accepted admin snapshots, lifecycle anchors, privacy/invalidation, second source | Required P0 chain surface for complete SDK; scoped non-complete releases may exclude it only while preserving no-complete-SDK wording. |
| `obelisk.permissions_admin.v1` | `promoted` | promoted player identity/principal | Required P0 chain surface for complete SDK; scoped non-complete releases may exclude it only while preserving no permission/admin SDK wording. |
| `obelisk.command_chat_response_path.v1` | `promoted` | promoted player identity/principal and permissions/admin | Required P0 chain surface for complete SDK; scoped non-complete releases may exclude it only while preserving no reply/send-chat/response-path wording. |
| `obelisk.commands_replies.v1` | `promoted` | promoted player identity, permissions/admin, and command/chat response path | Required P0 chain surface for complete SDK; scoped non-complete releases may exclude it only while preserving no command SDK/router wording. |
| `obelisk.inventory_items_mutation.v1` | `promoted`, `excluded`, or `post-v1` | player/inventory/item identity plus rollback/privacy controls | Name Inventory SDK, Items SDK, give/remove item, kits/rewards, engrams/progression, lookup, item handles, mutation, return override, and `ResourceHandle`. |
| `obelisk.structure_census.v1` | `promoted` or `excluded` | copied structure evidence, privacy/redaction, identity policy if exposed | Name StructureEvents SDK, structure census, structure identity, lookup, build placement policy, no-collision policy, and ownership lookup. |
| `obelisk.object_identity_resource_handle.v1` | `promoted`, `excluded`, or `post-v1` | lifecycle/reuse semantics, privacy/redaction, paired runtime ResourceHandle evidence | Name ResourceHandle, object identity, object lookup, post-callback handles, persistent handles, serial reuse/wraparound, mutation, and return override. |
| `obelisk.mission_transfer_dino_tribe.v1` | `promoted` or `excluded` | each module promoted as a narrow copied ABI or explicitly left out | Name Mission SDK, Transfer SDK, Dino SDK, dino colors/cosmetics/carry rules, Tribe SDK, tribe MOTD/notices/policy, Buff/status SDK, teleport/spawn, ownership lookup, and cross-map correlation. |
| `obelisk.player_services_economy_mobility.v1` | `promoted`, `excluded`, or `post-v1` | identity, permissions/admin, storage/persistence, audit/rollback/abuse controls | Name economy, shops, rewards, kits, stats, homes, teleport, safe zones, area policy, timed notices, and cross-instance persistence. |
| `obelisk.operator_ingress_storage.v1` | `promoted`, `excluded`, or `post-v1` | secret-safe ingress, storage schema/migration, queue drain, audit, encoding, lifecycle policy | Name RCON, operator reload command API, Unicode/operator text encoding, webhooks, database/storage, secret manager, external ingress, and cross-instance storage. |
| `obelisk.gameplay_tick_callbacks.v1` | `promoted`, `excluded`, or `post-v1` | cadence, budget, threading, hitch/backpressure, lifecycle, shutdown semantics | Name server tick callbacks, UE gameplay tick callbacks, module/per-frame hooks, and gameplay timers. |
| Promoted-experimental copied surfaces | `promoted`, `excluded`, or `post-v1` | full public SDK promotion evidence for each surface | Name `GameplayPolicyEvent`, `ChatMessageEvent`, plugin-local chat routing, and inventory copied signals if they remain outside v1. |
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

Surfaces marked `promoted-experimental-only` can be useful copied-data surfaces, but they
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
pre-identity installed-SDK foundation usefulness is insufficient for `v1.0 stable` until
the P0 dependency chain is promoted with evidence and non-chain blockers are promoted or
explicitly named as excluded/post-v1 in the release statement.
