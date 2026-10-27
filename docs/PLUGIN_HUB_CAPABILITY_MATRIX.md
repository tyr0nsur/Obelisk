> Nota histórica, 27 de octubre de 2026: esta planificación precede la
> integración de la suite y del panel. Consultar el
> [estado actual del ecosistema](OBELISKNATIVE_ECOSYSTEM.md) para el ámbito
> vigente. Los requisitos de evidencia se conservan; las restricciones de
> planificación anteriores no sustituyen las instrucciones actuales del operador.

# Plugin Hub Capability Matrix

Status: post-SDK-complete planning only.

This matrix is an archived contributor-facing planning aid for future Obelisk Plugin Hub
work. It maps common modder intents to current Obelisk primitives and parked post-SDK
support tiers.
It must not drive current engineering priority while the complete SDK blocker chain is
open.
`PLUGIN_HUB_FOUNDATION_V1.md` defines the first foundation seed contract that this matrix
builds on. The `Foundation V1` label means the first reviewed foundation/intake contract
revision for contributor readiness; it is not Obelisk SDK v1, `v1.0 stable`, or a Plugin
Hub completion claim.

It is not a compatibility promise for ArkApi plugins, not a module SDK roadmap freeze, and
not a replacement for promotion gates. If a row says "not ready", plugins must not work
around the gap with raw UE pointers, `ProcessEvent` mutation, object lookup, or copied
ArkApi implementation patterns.

ArkApi/AseApi names and the local `NextGenPlugins` clones are names and demand signals for
future Plugin Hub categories only. Treat those plugin families as evidence of requested
capability areas, not as architecture, ergonomics, portable behavior, source, ABI,
constants, schemas, command parsers, or implementation patterns. They are also not sources
for public contract
structs/events/descriptors/API tables. Rebuild every promoted surface through Obelisk
reflection, explicitly named second-source target sets, copied C ABI contracts, and
runtime safety gates.
The detailed local inventory lives in
`docs/research/2026-05-30-nextgenplugins-reference-inventory.md` and records provenance for
demand analysis only; it is not license clearance, runtime evidence, an ArkApi
compatibility target, or an ABI reference.

## Deferred Support Boundary

Plugin Hub seed work resumes after SDK completion. At that point it can start with
lifecycle/config/logging skeletons, descriptor/catalog consumers, and process-local timer
utilities that use the public C ABI with fail-closed capability checks. Copied `ChatMessageEvent` parsing and
copied `GameplayPolicyEvent` auditing may remain useful experimental seed examples, but
they are not production Plugin Hub modules, public command SDK/router surfaces, replies,
permissions, identity, send-chat, moderation, policy-enforcement SDKs, or compatibility
targets for ArkApi plugin families.

Future release-supported seeds should start from lifecycle/config/logging plugin skeletons,
descriptor/catalog readers, and process-local timer utilities. Passive copied chat
parsing and copied policy auditing are experimental examples only. Permissions/admin,
commands/replies/send-chat/broadcast, economy, kits, homes, teleport, and item grants
remain blocked until promoted identity/principal, permissions/admin, command routing,
response path, persistence/storage, and safe mutation/grant surfaces exist.

Every higher-level demand category below remains planning-only until its own copied-data
payload, identity/privacy policy, lifecycle cleanup, persistence or ingress design where
needed, SDK consumer tests, and exact release-readiness second-source target sets are
promoted. Planning-only, internal-layout, consume-only, or test-only evidence is not
public SDK evidence.

`v1.0` is the planned completion gate for a complete public SDK claim, not just a stable
core runtime. The foundation rows below are the starting layer; any future stable SDK
claim requires the blocked high-demand categories to be either promoted through
Obelisk-native copied ABI contracts and evidence, or explicitly left outside the `v1.0`
support statement so plugin authors do not mistake a partial primitive for a complete Ark
server modding framework.

## Support Tier Legend

- `parked release-supported seed after SDK completion`: future support tier for scoped
  Obelisk-native examples that use only the current public C ABI, fail-closed capability
  checks, safe-disabled config, and process-local ownership.
- `experimental seed only`: allowed for explicitly labeled pattern examples that teach
  copied-data callback handling, but not supported as production Plugin Hub modules or as
  general chat, command/router, replies, permissions, send-chat, policy, structure,
  inventory, identity, moderation, mutation, or enforcement SDKs.
  In compact boundary wording: not supported as production Plugin Hub modules or as
  general chat, command, policy, structure, inventory, identity, mutation, or enforcement
  SDKs.
- `blocked` and `blocked except experimental auditing`: backlog demand only. These lanes
  need their own copied-data ABI design, privacy/lifecycle rules, consumer tests, and
  evidence gates before plugin authors should build public examples around them.

## Contributor Triage Rule

Plugin Hub work is parked until the complete SDK blocker chain is resolved. Start with
`PLUGIN_HUB_SEED_BOUNDARY.md` only when archived planning is explicitly requested or when
post-SDK-complete Plugin Hub work resumes.

When that future work resumes, start only from rows marked
`parked release-supported seed after SDK completion`.
Rows marked `experimental seed only` may be used for clearly labeled pattern examples, not
production modules. Rows marked `blocked` or `blocked except experimental auditing` should
produce design notes, evidence plans, or guardrail tests only; do not start first-party
examples, SDK wrappers, compatibility shims, or public docs that imply those backlog
modules are supported.

## Foundation-To-Roadmap Alignment

For new contributors, the roadmap maps to this matrix in one direction only:

- `hub foundation` means parked post-SDK-complete seed planning for lifecycle/config/logging,
  descriptor/catalog consumers, timers, packaging, and fail-closed capability checks.
- `gameplay policy backing` means preserving evidence and tests for already promoted
  copied/redacted `GameplayPolicyEvent` fields from exact release-readiness target sets
  such as `minimal-second-source-intake`, `item-return-only-policy-slice`, and
  `structure-observer-intake`; it is not a new Inventory, Items, StructureEvents, or
  enforcement SDK.
- `internal recognizer planning` means docs, fixtures, and offline copied-bool planning
  for named targets; it is not runtime observation, public callbacks, public module
  capabilities, identity, lookup, mutation, or return override.

Demand dictionaries can decide which blocked rows deserve clearer notes or evidence
plans, but only a named promotion gate can move a row's support tier. That gate must name
the exact release-readiness target sets.

## Dictionary-To-Primitive Rule

The matrix maps demand families to the first Obelisk primitive that can honestly teach a
starter SDK pattern; it does not map a popular plugin family to a rebuildable Plugin Hub module.
Names from ArkApi/AseApi or local `NextGenPlugins` can corroborate demand, but they do not
widen a row's support tier.

For example, lifecycle/crash/reload demand maps only to lifecycle, config, logging, and
shutdown-cleanup skeletons. It does not promote plugin watchdogs, hot reload, process
restart, server recovery, or operator reload commands. Timed notices map to
process-local timers only when no chat send, broadcast, command, permission, persistence,
or cross-process scheduling behavior is implied. Economy, shops, kits, rewards, homes,
teleport, safe zones, area policy, mobility, RCON, tribe notices, and structure tools
remain blocked even when a subset of their timing, logging, descriptor, or passive
parsing needs could be demonstrated by a core primitive.

## NextGenPlugins Demand Snapshot

The local dictionary currently points to these high-demand Plugin Hub categories.
ArkApi/AseApi and `NextGenPlugins` names corroborate broad demand families only. The
status below describes only what Obelisk can expose safely today or after promotion
gates; it does not promise ArkApi plugin compatibility.

| Priority | Category | Post-RC support tier | Safe interpretation |
| --- | --- | --- | --- |
| 1 | Lifecycle, descriptors, logging, config, local timers | parked release-supported seed after SDK completion | Build native examples around current core primitives; process restart/crash management is not public SDK surface |
| 2 | Passive chat parsing and plugin-local text routing | experimental seed only | Use copied `ChatMessageEvent` for plugin-local parsing/routing only; no public command SDK/router, sender identity, replies, permissions, blocking, send-chat, or moderation contract |
| 3 | Copied structure/item policy auditing | experimental seed only | Use copied `GameplayPolicyEvent` only for observational audits of event kinds from `minimal-second-source-intake`, `item-return-only-policy-slice`, and `structure-observer-intake`; no StructureEvents SDK, Inventory SDK, Items SDK, identity, mutation, enforcement, or return override |
| 4 | Timed notices and chat broadcasts | blocked | Owner-token timers exist, but public response path, send-chat/broadcast policy, command routing, permissions/admin, persistence, and cross-process scheduling are not promoted |
| 5 | Permissions/admin query checks | blocked | Dependency-order note only, not an immediate next public slice: query-only authorization requires copied identity/principal plus permissions/admin policy first; groups, grants, admin actions, storage, RCON, and operator reload stay excluded; command routing and response path also remain blocked |
| 6 | RCON/operator I/O and Unicode text | blocked | Needs secret-safe ingress, audit policy, encoding rules, and command lifecycle |
| 7 | Economy, shops, kits, rewards, stats | blocked | Needs identity/principal, permissions/admin, command routing, response path, persistence/storage, item grant/mutation, and event evidence |
| 8 | Homes, teleport, safe zones, area policy | blocked | Needs location/area data, identity/principal, permissions/admin, command routing, response path, combat/enemy restrictions, and safe teleport/mutation/enforcement contracts |
| 9 | Structure counts, placement, ownership, collision policy | blocked except experimental auditing | Only copied policy observer examples are experimental; census, ownership, placement denial, collision control, and mutation are not public surfaces |
| 10 | Dino colors, carry rules, spawn/cosmetic policy | blocked | Needs dino/player identity, classification, interaction events, and safe mutation/enforcement |
| 11 | Tribe MOTD, tribe-facing notices, and tribe policy | blocked | Needs tribe/player identity, privacy policy, send-chat/broadcast or command surface, and moderation/visibility rules |
| 12 | Engrams, inventory, item give/remove flows | blocked | Needs player/inventory/item identity, permissions/admin where gated, command routing and response path where user-triggered, item grant/mutation APIs, rollback, and privacy policy |
| 13 | Shared persistence, database-backed state, webhook services | blocked | Config files are available only for plugin config; no Obelisk storage service, database schema/migration contract, secret manager, webhook client, or cross-instance persistence API |

### Top Demand Family Routing

These demand families are visible enough to keep in contributor planning, but they do not
create new Plugin Hub seed support. Route proposals to the blocker named below unless a
future promotion gate changes the support tier.

| Demand family | Route to current surface/blocker | Public wording boundary |
| --- | --- | --- |
| Economy/storage | `obelisk.player_services_economy_mobility.v1`, `obelisk.operator_ingress_storage.v1`, plus identity, permissions, command-response, and mutation dependencies | Backlog/design only; no economy, shop, reward, database, webhook, storage service, or cross-instance persistence API |
| Inventory mutation | `obelisk.inventory_items_mutation.v1`; experimental copied signal evidence may use `obelisk.inventory_item_copied_signals.v1` only as observation | No Inventory SDK, Items SDK, item identity, lookup, give/remove, mutation, rollback, or return override |
| Structure/build policy | `obelisk.structure_census.v1`; copied `GameplayPolicyEvent` policy observation remains experimental only | No StructureEvents SDK, structure identity, ownership lookup, placement denial, no-collision control, mutation, enforcement, or return override |
| Player mobility | `obelisk.player_services_economy_mobility.v1` | No homes, teleport, safe-zone, area-policy, persistent mobility state, or gameplay timer API |
| Mission/transfer/dino/tribe/buff | `obelisk.mission_transfer_dino_tribe.v1` leaf decisions | Backlog/design only; no Mission SDK, Transfer SDK, Dino SDK, Tribe SDK, Buff/status SDK, dino mutation/cosmetics/carry rules, tribe MOTD/notices, ownership lookup, teleport/spawn API, or cross-map correlation |

`parked release-supported seed after SDK completion` means an Obelisk-native plugin can
be written and documented as a future supported Plugin Hub seed against the stated public
ABI slice only after SDK completion. `experimental seed only` means the example can teach
copied-data callback patterns, but it should not be marketed as a production Plugin Hub
module or as general chat, command/router, replies, permissions, send-chat, moderation,
policy, structure, or inventory SDK availability.
Neither tier means the corresponding ArkApi plugin family can be ported, that command or
identity semantics exist, or that blocked dependencies can be simulated through raw game
access.

The common blocked chain is identity/principal -> permissions/admin -> command routing ->
response path, with send-chat/broadcast, persistence/storage, and safe mutation/grant
surfaces added where the feature needs them. Economy, kits, homes, teleport, item grants,
permissions/admin checks, commands, replies, send-chat, and broadcast must not be
documented as release-supported seeds by pointing at only timers, logging, descriptors, or
passive copied chat/policy examples.

Command/principal routing is blocked as a lifecycle and callback-ownership surface, not
just a missing parser. A future Plugin Hub command surface must use a new copied C ABI
entry with a named capability bit captured at plugin init, a nonzero `plugin_owner_token`,
owner-token handle registration, owner-scoped unregister, plugin-owner cleanup on init
failure or unload before `dlclose`, callback-scope copied payloads, and principal
privacy/invalidation rules. Do not route command/principal callbacks through ownerless
registrations, process-global capability state, raw `ProcessEvent`, debug gates, or the
experimental plugin-local `ChatMessageEvent` parsing lane.

| Modder intent | Use now | Status | Must not imply |
| --- | --- | --- | --- |
| Load a Linux-native plugin | `ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init`, optional `ObeliskPlugin_Shutdown` | Core-first RC baseline | Hot reload of Obelisk itself, detached workers, or background ingress without shutdown proof |
| Log through Obelisk | `ObeliskApi::LogInfo`, `LogWarn`, and `LogError` after `struct_size` checks | Core-first RC baseline | Long-lived ownership of callback data or cross-thread logging contracts not proven by the plugin |
| Discover resource categories | `DescribeResourceKind` | Promoted metadata | Resource identity, object lookup, persistent handles, or correlation between events |
| Discover promoted policy event kinds | `DescribeGameplayPolicyEventKind` | Promoted metadata | No complete gameplay inventory, public module SDK, mutation path, or return override |
| Observe copied structure/item policy data | `GameplayPolicyEvent` with owner-token registration for `minimal-second-source-intake`, `item-return-only-policy-slice`, and `structure-observer-intake` release-readiness target sets only | v0.1 copied-data ABI surface; promoted-experimental copied-data seed, not v1-complete | Public `StructureEvents`, Inventory SDK, Items SDK, UE pointers, player/item/structure identity, mutation, or return override |
| Parse copied chat text locally | `ChatMessageEvent` with owner-token registration; `chat-message-intake` is the exact release-readiness target set | Notification-only v0.1-rc ABI surface; experimental local parsing seed | Public command SDK/router, sender identity, replies, permissions, moderation, chat blocking, or send-chat API |
| Run process-local scheduled work | Owner-token timers | Promoted v0.1 core primitive | UE/gameplay timers, cluster scheduler, persistent ids, permission system, or command router |
| Inspect descriptor output safely | `oDescriptorCatalog` | First-party metadata example | Resource discovery, callback subscription, identity, lookup, mutation, or return override |
| Build an installed-SDK consumer | `examples/sdk_minimal_plugin`, `examples/sdk_descriptor_catalog`, and `examples/sdk_timer_plugin` with `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and `Obelisk::obelisk_sdk` | Installed SDK starter seed, descriptor seed, and timer seed | Runtime reference-plugin wiring, gameplay authority, module SDK coverage, private runtime headers, or ArkApi plugin portability |
| Study an installed-SDK copied policy audit pattern | `examples/sdk_inventory_policy_audit` with `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and `Obelisk::obelisk_sdk` | Experimental pattern only | Inventory SDK, Items SDK, identity, lookup, mutation, return override, commands, permissions, send-chat, storage, policy enforcement, or ArkApi compatibility |
| Study in-tree reference plugins | `plugins/oBaseEvents`, `plugins/oProcessTimer`, descriptor examples | Reference plugins | Starter installed-SDK consumer contract, gameplay authority, module SDK coverage, or ArkApi plugin portability |
| Use raw `ProcessEvent` callbacks | Filtered callbacks behind explicit debug gates | Debug-gated runtime plumbing | Stable gameplay API, borrowed pointer lifetime, raw param API, or public Plugin Hub dependency |
| Commands, permissions, economy, kits, shops, RCON | No public Obelisk SDK yet | Not ready | ArkApi compatibility, player identity, reply/send-chat, database service, or operator command lifecycle |
| Persistent storage, databases, webhooks | Plugin-owned config files only | Not ready | Public storage SDK, database service, schema/migration contract, secret management, webhook/RCON integration, or cross-instance state |
| Inventory/item identity and mutation | No public Obelisk SDK yet | Not ready | `ResourceHandle`, `ItemNetID`, inventory lookup, item mutation, give/remove item, or return override |
| Players, tribes, dinos, buffs/status, missions, transfers | No public Obelisk SDK yet | Not ready | Public identity, ownership lookup, mutation, teleport/spawn APIs, transfer payload decoding, or cross-map correlation |
| Player identity lifecycle intake | `players-identity-lifecycle-intake` research guidance only | Planning-only | Stable player identity, lookup, permissions, send-chat, moderation, public SDK, runtime hooks, or release readiness |
| Mission copied-bool planning and mission demand | Internal/test-only research notes; `mission-copied-bool-policy-slice` internal/test-only v0.2 lane | Planning-only/test-only | Not a Production Plugin Hub mission module; no public Mission SDK, Mission module readiness, ArkApi mission compatibility, command SDK dependency, mission identity, mission state mutation, runtime observation approval, or reward/transfer authority |
| Structure census/proximity | `structure-aggregate-census-planning` research guidance only | Planning-only | Public GObjects traversal, structure handles, exact coordinates, ownership lookup, linked-structure traversal, StructureEvents SDK, or mutation |
| Structure build placement policy | No public Obelisk SDK yet | Not ready | Ark-style build placement compatibility, placement denial, no-collision behavior, structure identity, location disclosure, mutation, or return override |

## Current Safe Route

For plugin authors today, the supported installed-SDK foundation surfaces are
lifecycle/config/logging, descriptor-driven discovery, and process-local timers; treat
Plugin Hub seeds as parked until SDK completion. In this section,
`promoted` means a copied, capability-gated ABI
entry with an exact release-readiness second-source target set can be discovered or
subscribed to by explicitly experimental copied-data examples; it does not turn copied
chat/policy examples into production Plugin Hub modules, command/router or policy SDKs,
replies, permissions, send-chat, enforcement APIs, identity APIs, moderation APIs,
mutation APIs, or ArkApi compatibility.

1. Check `abi_version`, `struct_size`, capability bits, and function pointers.
2. Use `DescribeResourceKind` to discover promoted categories.
3. Use `DescribeGameplayPolicyEventKind` to discover promoted copied policy kinds.

Experimental copied-data examples may then:

1. Subscribe only to promoted copied events with owner-token handles.
2. Route plugin-local logic by copied `resource_kind`, `event_kind`, and `field_mask`.

Plugins must copy any callback data they need after the callback returns. Runtime-owned
event data is callback-scope only.

## Post-v0.1 Creator Ladder

This ladder is archived post-SDK-complete planning. It must not be used as an active work
queue before the complete SDK blocker chain is resolved. When Plugin Hub work resumes,
prefer plugins that stay inside the current ABI and keep the support tier explicit:

Installed-SDK consumer seed:

1. `examples/sdk_minimal_plugin` as the starter package consumer that builds against the
   installed SDK; this is the starter template.
2. `examples/sdk_descriptor_catalog` as the installed-SDK descriptor/catalog seed.
3. `examples/sdk_timer_plugin` as the installed-SDK timer seed for owner-token scheduled
   work and shutdown cleanup.

These three installed-SDK foundation templates are the starter template, the
descriptor catalog template, and the owner-token timer template. Their no-promises are
part of the template contract: they do not promise identity/principal,
permissions/admin, command routing, replies/send-chat/broadcast, storage,
inventory/item/structure modules, mutation, return override authority, cross-process
scheduler, ArkApi/AseApi portability, or Obelisk SDK v1 completion.

Release-supported seed lanes under `plugins/`:

1. Lifecycle/config/logging skeletons with safe-disabled config.
2. Descriptor consumers that print sanitized promoted category/event metadata.
3. Timer utilities for plugin-owned process-local periodic work.

Experimental pattern examples only:

1. Passive chat text parsers that do plugin-local routing/parsing only.
2. Copied policy auditors over target-set-promoted `GameplayPolicyEvent` kinds named
   above.

The installed-SDK examples currently start at `examples/sdk_minimal_plugin` and include
`examples/sdk_descriptor_catalog` for descriptor reads and `examples/sdk_timer_plugin` for
the promoted timer surface. `examples/sdk_inventory_policy_audit` is separate from that
release-supported example set; it is an experimental copied policy audit pattern only.
Under `plugins/`, `oBaseEvents`, `oProcessTimer`, and `oDescriptorCatalog` cover the
release-scope foundation, while `oPolicyAudit`, `oChatLogger`, and `oChatAudit` cover the
experimental copied policy and copied chat slices. These are installed-SDK foundation
templates now and parked Plugin Hub seed lanes after SDK completion; specifically, they
are archived examples and planning references, not active Plugin Hub modules, not
production Hub work, and not promises that copied chat/policy auditing is generally
available.
Before any new first-party Plugin Hub work resumes, the SDK blocker chain must be
complete. Until then, existing copied-data examples may still be useful as guardrail
fixtures, but they are not a graduation path and no additional public category is
supported by the current ABI.
If only default release examples are counted, passive copied chat auditing/parsing is a
candidate for promotion review before copied policy auditing, not a promised graduation
path. If experimental examples are counted too, no additional public category is
supported by the current ABI.

Do not start public examples with permissions, command routers, replies, send-chat,
economy, homes, RCON, storage/database services, webhooks, inventory, dinos, tribes,
missions, transfers, structure enforcement, or item grants. Those are valid demand
signals, but they become Plugin Hub examples only after their own identity, privacy,
persistence, operator-ingress, mutation/enforcement, lifecycle, and exact target-set
evidence gates are satisfied.

## Plugin Hub Direction

Plugin Hub direction is parked until SDK completion. The first useful Plugin Hub seed
examples should be built from surfaces that already exist after that point. The
installed-SDK starter
consumers are `examples/sdk_minimal_plugin`,
`examples/sdk_descriptor_catalog`, and `examples/sdk_timer_plugin`; `plugins/*` contains
in-tree runtime reference plugins.

- lifecycle/config/logging examples;
- descriptor/catalog consumers;
- process-local timer utilities.

These are installed-SDK foundation templates now and parked Plugin Hub seed lanes after
SDK completion. Copied `GameplayPolicyEvent` auditors and
copied `ChatMessageEvent` parsers may still be useful experimental pattern examples, but
they must be labeled as experimental and must not claim policy enforcement, general chat,
commands, identity, replies, moderation, send-chat, or production Plugin Hub availability.
They also must not claim public routers or permissions.

Higher-level ArkApi-style families such as permissions, economy, kits, homes, safe zones,
RCON, storage/database services, webhooks, inventory tools, dino tools, tribe tools, and
build-placement policy remain future work. Each requires its own copied-data evidence, ABI
design, privacy policy, lifecycle tests, and exact release-readiness target-set promotion
gate.

Planning should keep the full demand surface visible: players, tribes, dinos, items,
structures, permissions, commands, admin, transfers, missions, timers, storage, economy,
homes, teleport, safe zones, and mobility.
Current attention on passive chat, `ResourceHandle` blockers, or structure build-placement
triage must not turn those lanes into the Plugin Hub center, nor imply SDK availability
for the wider surface.

The safest future structure direction is likely aggregate/census-style data, such as
counts by copied category or bounded proximity signals, because it can be designed without
public structure handles. The current `structure-aggregate-census-planning` target set is
planning-only: it is not release readiness, not public SDK evidence, and not a public
StructureEvents surface. A future promotion still needs a separate design that avoids
public GObjects traversal, exact coordinates, ownership lookup, linked-structure
traversal, mutation, and cross-event identity claims.
