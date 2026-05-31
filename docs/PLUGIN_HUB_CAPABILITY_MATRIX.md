# Plugin Hub Capability Matrix

This matrix is a contributor-facing planning aid for future Obelisk Plugin Hub work. It
maps common modder intents to the public Obelisk surface that is safe today and separates
post-RC production seed work from experimental copied-data examples.
`PLUGIN_HUB_FOUNDATION_V1.md` defines the minimal foundation contract that this matrix
builds on.

It is not a compatibility promise for ArkApi plugins, not a module SDK roadmap freeze, and
not a replacement for promotion gates. If a row says "not ready", plugins must not work
around the gap with raw UE pointers, `ProcessEvent` mutation, object lookup, or copied
ArkApi implementation patterns.

The local `NextGenPlugins` clones are a names and demand dictionary for future Plugin Hub
categories only. Treat their plugin families as evidence of operator needs, not as
portable behavior, source, ABI, constants, schemas, command parsers, or implementation
patterns. Rebuild every promoted surface through Obelisk reflection, second-source
fixtures, copied C ABI contracts, and runtime safety gates.
The detailed local inventory lives in
`docs/research/2026-05-30-nextgenplugins-reference-inventory.md` and records provenance for
demand analysis only; it is not license clearance, runtime evidence, an ArkApi
compatibility target, or an ABI reference.

## Post-RC Support Boundary

Post-RC production-supported Plugin Hub seed work is limited to lifecycle/config/logging
skeletons, descriptor/catalog consumers, and process-local timer utilities that use the
current C ABI with fail-closed capability checks. Copied `ChatMessageEvent` parsing and
copied `GameplayPolicyEvent` auditing may remain useful experimental seed examples, but
they are not production Plugin Hub modules, command/chat SDKs, policy-enforcement SDKs, or
compatibility targets for ArkApi plugin families.

Every higher-level demand category below remains planning-only until its own copied-data
payload, identity/privacy policy, lifecycle cleanup, persistence or ingress design where
needed, SDK consumer tests, and second-source/runtime evidence gate are promoted.

## Support Tier Legend

- `production seed available`: supported for narrow Obelisk-native examples that use only
  the current public C ABI, fail-closed capability checks, safe-disabled config, and
  process-local ownership.
- `experimental seed only`: allowed for explicitly labeled pattern examples that teach
  copied-data callback handling, but not supported as production Plugin Hub modules or as
  general chat, command, policy, structure, inventory, identity, mutation, or enforcement
  SDKs.
- `blocked` and `blocked except experimental auditing`: backlog demand only. These lanes
  need their own copied-data ABI design, privacy/lifecycle rules, consumer tests, and
  evidence gates before plugin authors should build public examples around them.

## Contributor Triage Rule

When selecting a Plugin Hub seed, start only from rows marked `production seed available`.
Rows marked `experimental seed only` may be used for clearly labeled pattern examples, not
production modules. Rows marked `blocked` or `blocked except experimental auditing` should
produce design notes, evidence plans, or guardrail tests only; do not start first-party
examples, SDK wrappers, compatibility shims, or public docs that imply those backlog
modules are supported.

## Dictionary-To-Primitive Rule

The matrix maps demand families to the first Obelisk primitive that can honestly teach a
small pattern; it does not map a popular plugin family to a rebuildable Plugin Hub module.
Names from ArkApi/AseApi or local `NextGenPlugins` can corroborate demand, but they do not
widen a row's support tier.

For example, lifecycle/crash/reload demand maps only to lifecycle, config, logging, and
shutdown-cleanup skeletons. It does not promote plugin watchdogs, hot reload, process
restart, server recovery, or operator reload commands. Timed notices map to
process-local timers only when no chat send, broadcast, command, permission, persistence,
or cross-process scheduling behavior is implied. Economy, shops, kits, rewards, homes,
safe zones, RCON, tribe notices, and structure tools remain blocked even when a subset of
their timing, logging, descriptor, or passive parsing needs could be demonstrated by a
core primitive.

## NextGenPlugins Demand Snapshot

The local dictionary currently points to these high-demand Plugin Hub categories.
ArkApi/AseApi names corroborate the same broad families for demand analysis only. The
status below describes only what Obelisk can expose safely today or after promotion gates;
it does not promise ArkApi plugin compatibility.

| Priority | Category | Post-RC support tier | Safe interpretation |
| --- | --- | --- | --- |
| 1 | Lifecycle, descriptors, logging, config, local timers | production seed available | Build native examples around current core primitives; process restart/crash management is not public SDK surface |
| 2 | Passive chat parsing and plugin-local text routing | experimental seed only | Use copied `ChatMessageEvent` for local parsing only; no command SDK, sender identity, replies, blocking, or moderation contract |
| 3 | Copied structure/item policy auditing | experimental seed only | Use copied `GameplayPolicyEvent` only for observational audits of promoted event kinds; no StructureEvents SDK, Inventory SDK, identity, mutation, enforcement, or return override |
| 4 | Timed notices and chat broadcasts | blocked | Owner-token timers exist, but public send-chat/broadcast policy is not promoted |
| 5 | Permissions/admin groups | blocked | Needs identity, persistence, privacy-safe grants/checks, and operator reload policy |
| 6 | RCON/operator I/O and Unicode text | blocked | Needs secret-safe ingress, audit policy, encoding rules, and command lifecycle |
| 7 | Economy, shops, kits, rewards, stats | blocked | Needs commands, identity, permissions, persistence, item mutation, and event evidence |
| 8 | Homes, teleport, safe zones, area policy | blocked | Needs location/area data, identity, combat/enemy restrictions, and safe mutation/enforcement contracts |
| 9 | Structure counts, placement, ownership, collision policy | blocked except experimental auditing | Only narrow copied policy observer examples are experimental; census, ownership, placement denial, collision control, and mutation are not public surfaces |
| 10 | Dino colors, carry rules, spawn/cosmetic policy | blocked | Needs dino/player identity, classification, interaction events, and safe mutation/enforcement |
| 11 | Tribe MOTD, tribe-facing notices, and tribe policy | blocked | Needs tribe/player identity, privacy policy, send-chat/broadcast or command surface, and moderation/visibility rules |
| 12 | Engrams, inventory, item give/remove flows | blocked | Needs player/inventory/item identity, progression or item mutation APIs, rollback, and privacy policy |
| 13 | Shared persistence, database-backed state, webhook services | blocked | Config files are available only for plugin config; no Obelisk storage service, database schema/migration contract, secret manager, webhook client, or cross-instance persistence API |

`production seed available` means an Obelisk-native plugin can be written and documented
as a supported Plugin Hub seed against the stated current public ABI slice. `experimental
seed only` means the example can teach copied-data callback patterns, but it should not be
marketed as a production Plugin Hub module or as general chat, command, policy, structure,
or inventory SDK availability. Neither tier means the corresponding ArkApi plugin family
can be ported, that command or identity semantics exist, or that blocked dependencies can
be simulated through raw game access.

| Modder intent | Use now | Status | Must not imply |
| --- | --- | --- | --- |
| Load a Linux-native plugin | `ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init`, optional `ObeliskPlugin_Shutdown` | Stable baseline | Hot reload of Obelisk itself, detached workers, or background ingress without shutdown proof |
| Log through Obelisk | `ObeliskApi::LogInfo`, `LogWarn`, and `LogError` after `struct_size` checks | Stable baseline | Long-lived ownership of callback data or cross-thread logging contracts not proven by the plugin |
| Discover resource categories | `DescribeResourceKind` | Promoted metadata | Resource identity, object lookup, persistent handles, or correlation between events |
| Discover promoted policy event kinds | `DescribeGameplayPolicyEventKind` | Promoted metadata | No complete gameplay inventory, public module SDK, mutation path, or return override |
| Observe promoted structure/item policy data | `GameplayPolicyEvent` with owner-token registration | Promoted copied-data ABI surface; experimental Plugin Hub seed | Public `StructureEvents`, Inventory SDK, Items SDK, UE pointers, player/item/structure identity, mutation, or return override |
| Parse copied chat text locally | `ChatMessageEvent` with owner-token registration | Minimal v0.1-rc ABI surface | Command SDK, sender identity, replies, moderation, chat blocking, or send-chat API |
| Run process-local scheduled work | Owner-token timers | Promoted v0.1 core primitive | UE/gameplay timers, cluster scheduler, persistent ids, permission system, or command router |
| Inspect descriptor output safely | `oDescriptorCatalog` | First-party metadata example | Resource discovery, callback subscription, identity, lookup, mutation, or return override |
| Build simple lifecycle/config examples | `oBaseEvents`, `oProcessTimer`, descriptor examples | Reference plugins | Gameplay authority, module SDK coverage, or ArkApi plugin portability |
| Use raw `ProcessEvent` callbacks | Filtered callbacks behind explicit debug gates | Debug-gated runtime plumbing | Stable gameplay API, borrowed pointer lifetime, raw param API, or public Plugin Hub dependency |
| Commands, permissions, economy, kits, shops, RCON | No public Obelisk SDK yet | Not ready | ArkApi compatibility, player identity, reply/send-chat, database service, or operator command lifecycle |
| Persistent storage, databases, webhooks | Plugin-owned config files only | Not ready | Public storage SDK, database service, schema/migration contract, secret management, webhook/RCON integration, or cross-instance state |
| Inventory/item identity and mutation | No public Obelisk SDK yet | Not ready | `ResourceHandle`, `ItemNetID`, inventory lookup, item mutation, give/remove item, or return override |
| Players, tribes, dinos, missions, transfers | No public Obelisk SDK yet | Not ready | Public identity, ownership lookup, mutation, teleport/spawn APIs, transfer payload decoding, or cross-map correlation |
| Player identity lifecycle intake | `players-identity-lifecycle-intake` research guidance only | Planning-only | Stable player identity, lookup, permissions, send-chat, moderation, public SDK, runtime hooks, or release readiness |
| Mission planning and mission demand | Demand/research notes only | Planning-only | Production Plugin Hub mission module, ArkApi mission compatibility, command SDK dependency, mission identity, mission state mutation, or reward/transfer authority |
| Structure census/proximity | No public Obelisk SDK yet | Not ready | Public GObjects traversal, structure handles, exact coordinates, ownership lookup, linked-structure traversal, or mutation |
| Structure build placement policy | No public Obelisk SDK yet | Not ready | `APrimalStructure.IsAllowedToBuild` compatibility, placement denial, no-collision behavior, structure identity, location disclosure, mutation, or return override |

## Current Safe Route

For plugin authors, the stable v0.1.x shape is descriptor-driven. In this section,
`promoted` means a copied, capability-gated ABI entry can be discovered or subscribed to;
it does not turn copied chat/policy examples into production Plugin Hub modules, command
or policy SDKs, enforcement APIs, identity APIs, mutation APIs, or ArkApi compatibility.

1. Check `abi_version`, `struct_size`, capability bits, and function pointers.
2. Use `DescribeResourceKind` to discover promoted categories.
3. Use `DescribeGameplayPolicyEventKind` to discover promoted copied policy kinds.
4. Subscribe only to promoted copied events with owner-token handles.
5. Route by copied `resource_kind`, `event_kind`, and `field_mask`.

Plugins must copy any callback data they need after the callback returns. Runtime-owned
event data is callback-scope only.

## Post-v0.1 Creator Ladder

For the first Plugin Hub seeds after `v0.1`, prefer plugins that stay inside the current
ABI and keep the support tier explicit:

Production-supported seed lanes:

1. Lifecycle/config/logging skeletons with safe-disabled config.
2. Descriptor consumers that print sanitized promoted category/event metadata.
3. Timer utilities for plugin-owned process-local periodic work.

Experimental pattern examples only:

1. Passive chat text parsers that do local routing only.
2. Copied policy auditors over promoted `GameplayPolicyEvent` kinds.

The current first-party examples already cover this safe seed set: `oBaseEvents`,
`oProcessTimer`, and `oDescriptorCatalog` cover the release-scope foundation, while
`oPolicyAudit`, `oChatLogger`, and `oChatAudit` cover the experimental copied policy and
copied chat slices. Those three are seed examples only, not production Plugin Hub modules
or promises that copied chat/policy auditing is generally available. After those examples,
the next honest first-party work is not a new ArkApi-style category; it is hardening,
documenting, or reviewing one of the existing copied-data examples against promotion
gates. If only default release examples are counted, passive copied chat
auditing/parsing is a candidate for promotion review before copied policy auditing, not a
promised graduation path. If experimental examples are counted too, no additional public
category is supported by the current ABI.

Do not start public examples with permissions, economy, homes, RCON, storage/database
services, webhooks, inventory, dinos, tribes, transfers, structure enforcement, or item
grants. Those are valid demand signals, but they become Plugin Hub examples only after
their own identity, privacy, persistence, operator-ingress, mutation/enforcement,
lifecycle, and evidence gates are satisfied.

## Plugin Hub Direction

The first useful Plugin Hub seed examples should be built from surfaces that already
exist:

- lifecycle/config/logging examples;
- descriptor/catalog consumers;
- process-local timer utilities.

Those are the production-supported seed lanes. Copied `GameplayPolicyEvent` auditors and
copied `ChatMessageEvent` parsers may still be useful experimental pattern examples, but
they must be labeled as experimental and must not claim policy enforcement, general chat,
commands, identity, replies, moderation, send-chat, or production Plugin Hub availability.

Higher-level ArkApi-style families such as permissions, economy, kits, homes, safe zones,
RCON, storage/database services, webhooks, inventory tools, dino tools, tribe tools, and
build-placement policy remain future work. Each requires its own copied-data evidence, ABI
design, privacy policy, lifecycle tests, and promotion gate.

Planning should keep the full demand surface visible: players, tribes, dinos, items,
structures, permissions, commands, admin, transfers, missions, timers, and storage.
Current attention on passive chat, `ResourceHandle` blockers, or structure build-placement
triage must not turn those lanes into the Plugin Hub center, nor imply SDK availability
for the wider surface.

The safest future structure direction is likely aggregate/census-style data, such as
counts by copied category or bounded proximity signals, because it can be designed without
public structure handles. It still needs a separate design that avoids public GObjects
traversal, exact coordinates, ownership lookup, linked-structure traversal, mutation, and
cross-event identity claims.
