# NextGenPlugins Reference Inventory

Date: 2026-05-30

## Scope

`/home/flowcommunity-ark/NextGenPlugins` is an operator-provided local clone of popular
ArkApi/Windows plugin sources for future Obelisk Plugin Hub planning.

Use this material only as a behavior and feature-priority reference. Do not copy Windows
ArkApi code, offsets, MSVC ABI assumptions, vtables, memory layouts, direct UE pointer API
patterns, or implementation details into Obelisk.

This note intentionally records demand categories and visible plugin-family names only.
It is not a source-mining checklist: do not use the clone to import signatures, constants,
call sequences, control flow, command parsers, database schemas, or wrapper patterns into
Obelisk.

## Local Inventory

Top-level collections:

- `/home/flowcommunity-ark/NextGenPlugins/Michidu-Ark-Server-Plugins`
- `/home/flowcommunity-ark/NextGenPlugins/ASE-Plugins`

Local source revisions observed on 2026-05-30:

- `Michidu-Ark-Server-Plugins`: `65ada1d42ac1`
- `ASE-Plugins`: `81a0a07637af`

Verification note: both roots currently expose the same visible plugin family set at
shallow depth. Treat duplicated repositories as one demand signal until a later Plugin Hub
matrix records exact source commits, licenses, and per-plugin provenance.

Observed plugin directories:

- `AdminsPermissions`
- `AllEngrams`
- `AlternativeCommands`
- `AntiFlyerCarry`
- `ArkAdvert`
- `ArkHomes`
- `ArkShop`
- `AtlasShop`
- `CustomChat`
- `DinoColors`
- `ExtendedRcon`
- `NoCollision`
- `Permissions`
- `PersonalOwnership`
- `PluginCrashManager`
- `SafeZone`
- `ShopRewards`
- `StructuresLimit`
- `TribeMotd`
- `UnicodeRcon`

The `Michidu-Ark-Server-Plugins` root declares an `ARK-Server-API` submodule, currently not
initialized in this local copy. Both visible top-level roots expose license/readme files,
but individual plugin provenance and licenses must still be checked before any derived
public Plugin Hub note. These revisions are provenance for demand analysis only; they are
not runtime evidence and do not authorize copied implementation, offsets, layouts, ABI
assumptions, or ArkApi compatibility claims.

## Value For Obelisk

This repository is useful after the Obelisk core API is stable enough to model plugin
replacement work. It can help rank public SDK surfaces by real plugin demand:

- permissions and admin capability model;
- economy/shop/rewards primitives;
- chat command ergonomics;
- homes/teleport/safe-zone style player interactions;
- tribe, structure, dino, and inventory policy use cases;
- RCON/operator integration;
- plugin crash/recovery and lifecycle expectations.

The visible demand clusters from the local clone are:

- permissions/admin: groups, temporary grants, tribe/player permissions, and operator
  checks;
- chat/commands: aliases, help, message routing, announcements, MOTD, and command
  responses;
- economy/rewards: shops, kits, points, kill rewards, database-backed balances, and
  reward hooks;
- homes/teleport/safe zones: cooldowns, costs, combat/enemy restrictions, PvP/building
  policies, and entry/exit behavior;
- structures/ownership: structure limits, ownership cleanup, no-collision/admin
  exceptions, and blueprint/category policies;
- dinos/items/inventory: dino colors/spawns, carry rules, give-item/shop flows, and
  inventory inspection needs;
- RCON/operator I/O: remote commands, reloads, broadcasts, and Unicode/text robustness;
- lifecycle/ops: plugin crash handling, timers, reload expectations, shutdown cleanup,
  and multi-instance configuration.

Observed ArkApi-facing concepts include chat commands, console commands, RCON commands,
timer callbacks, direct hooks such as player login/logout, item/shop/kits flows,
permissions group management, structure build policy, dino carry/color/reward hooks, and
RCON/operator utilities. These names are useful as candidate seeds only; every promoted
Obelisk equivalent still needs native Linux reflection/runtime evidence.

Quick local scan result: the cloned plugin area currently exposes 570
source/header/readme-like files. High-frequency ArkApi surfaces include chat, console,
and RCON command registration; timer callbacks; direct hooks; world/actor traversal;
chat/server messages; permissions; and save/respawn/build/damage-style gameplay hooks.
`StructuresLimit`, `SafeZone`, and `NoCollision` reinforce demand for a future structure
build-placement policy lane, but they do not promote `APrimalStructure.IsAllowedToBuild`
or any return-code semantics today.

Use this clone as a demand-map and dictionary source, not as source code to port.
Do not trust `DECLARE_HOOK` declarations as Linux ABI, direct UE pointer wrappers as safe
public API shape, or ArkApi return constants as accepted Linux ARK behavior.

## Constraints

- Keep the current Obelisk core route first: copied events, stable C ABI, owner-token
  lifecycle, descriptor metadata, no UE internals in public plugin APIs.
- Treat ArkApi plugin source as a feature dictionary only.
- Any future Obelisk Plugin Hub capability note must describe behavior at a high level,
  not copy implementation.
- Public APIs needed by these plugin families still require Obelisk promotion gates:
  copied payloads, second-source evidence where relevant, ABI tests, privacy policy,
  lifecycle cleanup, and no identity/mutation/return override unless explicitly promoted.

## Recommendation

Keep this local clone out of the Obelisk repository. Use the existing
`docs/PLUGIN_HUB_CAPABILITY_MATRIX.md` as the public boundary document and keep detailed
plugin-family provenance, license checks, and demand scans in research notes until the v1
core has stable copied surfaces, lifecycle cleanup, multi-instance config, and secret-safe
DB/webhook/RCON patterns.

Do not convert this inventory into a public compatibility promise.

Do not let this inventory pull internal evidence lanes into Plugin Hub scope prematurely.
For example, Transfer remains an internal evidence backlog item unless a concrete plugin
family creates demand for a public Transfer surface and the Obelisk promotion gates are
met. The current high-demand families are permissions/admin, economy/shop/rewards, chat
commands, homes/teleport/safe-zone, RCON/operator integration, structures, dinos, tribes,
and lifecycle/crash handling.

When a plugin family reveals a promising surface, create an Obelisk-native lane:

1. Name candidate functions/properties from the dictionary source.
2. Resolve exact Linux owner/name through reflection or offline analysis.
3. Capture sanitized evidence with SHA256, Obelisk commit, and artifact metadata.
4. Add fixture and second-source comparison.
5. Design a copied C ABI surface with explicit ownership, redaction, lifecycle cleanup,
   and plugin tests.
6. Only then expose it to Plugin Hub examples or public docs.

Non-roadmap candidate pressure order from this demand inventory:

This list is not a v1 delivery sequence, compatibility plan, or Plugin Hub roadmap. It is a
demand-ranked dependency sketch for future design reviews after the promotion gates above.

1. Hub foundation: lifecycle, descriptors, timers, config/logging, reload posture, and
   multi-instance-safe packaging.
2. Passive chat parsing and command-like local routing on top of copied `ChatMessageEvent`,
   without claiming a command, moderation, or reply/send-chat SDK.
3. Permissions/admin only after copied identity and privacy-safe grants/checks; do not use
   public `ResourceHandle` or UE pointers.
4. RCON/operator I/O only after secret-safe ingress, audit policy, and lifecycle rules.
5. Basic economy/rewards only after command-like routing, permissions, identity, and
   persistence are promoted, and still before any give-item or mutation surface.
6. Homes/safe zones/structures only after location, ownership, enforcement, and mutation
   contracts have their own evidence and promotion records.
7. Items, inventory, dinos, transfers, and missions remain investigation/internal unless
   copied-data, lifecycle, identity/privacy, and promotion gates are complete.

## Prioritized Demand Map

This table is a safe demand dictionary from visible plugin names and `PluginInfo.json`
descriptions only. It does not use plugin implementation, offsets, layouts, wrappers,
Windows ABI assumptions, or algorithms.

Status labels:

- `available`: a narrow Obelisk-native variant can be built from current public surfaces.
- `experimental`: Obelisk has partial/debug/promoted observer plumbing, but not a complete
  Plugin Hub category contract.
- `blocked`: requires new copied-data evidence, ABI design, privacy/lifecycle policy, and
  promotion gates before a public Plugin Hub surface.

| Priority | Demand category | Seen in local dictionary | Obelisk capability needed | Status |
| --- | --- | --- | --- | --- |
| 1 | Plugin lifecycle, descriptors, logging, config, local timers | `PluginCrashManager`, common config files | Existing plugin lifecycle, descriptor metadata, logging, owner-token timers, packaging guidance; restart/crash supervision remains future work | available |
| 2 | Chat text parsing and command-like routing | `CustomChat`, `AlternativeCommands` | Copied `ChatMessageEvent`, owner-token callbacks, process-local parsing, command registry design; replies, blocking, identity, and moderation remain future work | available |
| 3 | Timed broadcasts and notices | `ArkAdvert`, `TribeMotd` | Owner-token timers plus a future send-chat/broadcast surface and message policy | blocked |
| 4 | Permissions and admin groups | `Permissions`, `AdminsPermissions` | Stable player/admin identity, group/grant persistence, privacy-safe checks, operator reload policy | blocked |
| 5 | RCON/operator command I/O and Unicode-safe text | `ExtendedRcon`, `UnicodeRcon` | Secret-safe operator ingress, command lifecycle, encoding policy, audit logging | blocked |
| 6 | Economy, points, shops, and kits | `ArkShop`, `AtlasShop` | Commands, identity, permissions, persistence, item mutation/give flows, transaction-safe storage | blocked |
| 7 | Kill rewards and stats | `ShopRewards` | Copied kill/damage/death events, identity, dino/player classification, persistence | blocked |
| 8 | Homes and teleport | `ArkHomes` | Copied location/identity, cooldowns, permission checks, safe teleport mutation, combat/enemy restrictions | blocked |
| 9 | Safe zones and area policy | `SafeZone` | Bounded location/area model, entry/exit observation, damage/build/use enforcement contracts | blocked |
| 10 | Structure counts and limits | `StructuresLimit` | Promoted copied structure policy/census data, ownership/tribe identity, bounded counts; enforcement remains future work | experimental |
| 11 | Build placement and collision policy | `NoCollision` | Build-placement policy evidence, explicit deny/allow semantics, admin identity, no raw structure handles | blocked |
| 12 | Personal or tribe ownership cleanup | `PersonalOwnership` | Ownership identity, structure lookup/census, safe mutation/cleanup contract | blocked |
| 13 | Engram learning/unlock utilities | `AllEngrams` | Player identity, progression state, unlock mutation API, privacy and rollback policy | blocked |
| 14 | Dino cosmetics and spawn/color policy | `DinoColors` | Dino identity/classification, spawn/tame observation, safe cosmetic mutation | blocked |
| 15 | Flyer carry restrictions | `AntiFlyerCarry` | Mount/carry interaction events, player/dino/team identity, enforcement return path | blocked |
| 16 | Inventory and item grant/remove flows | shop/kits families | Inventory/item identity, copied item descriptors, give/remove mutation, failure and rollback semantics | blocked |
| 17 | Persistence-backed plugin data | shop, permissions, tribe/admin families | Secret-safe DB/config patterns, migrations, lifecycle cleanup, multi-instance boundaries; plugin-local files can exist without a shared service | blocked |
| 18 | Structure/item policy auditing | structure/shop/safe-zone families | Existing copied `GameplayPolicyEvent` observers and descriptor metadata; identity, mutation, and return override remain future work | available |

Near-term Plugin Hub demand should therefore start with foundation examples, passive chat
parsers, descriptor/timer utilities, and copied policy auditors. High-demand ArkApi-style
features are valuable prioritization signals, but most require identity, mutation,
persistence, operator ingress, and enforcement contracts that Obelisk has not promoted.

Fastest honest post-`v0.1` path for plugin creators:

1. Publish or refine small examples for lifecycle/config/logging, descriptors, timers,
   passive copied chat parsing, and copied policy auditing.
2. Keep command-like chat routing local and non-authoritative until identity, replies,
   moderation, and send-chat are promoted.
3. Treat permissions, RCON, economy, homes/safe zones, structures, dinos, tribes,
   transfers, inventory, and item mutation as design backlogs, not public examples.
4. When a backlog category is ready, start with an Obelisk-native design note and evidence
   plan before adding SDK symbols or first-party plugin examples.
