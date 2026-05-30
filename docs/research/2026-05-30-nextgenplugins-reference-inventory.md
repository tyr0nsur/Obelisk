# NextGenPlugins Reference Inventory

Date: 2026-05-30

## Scope

`/home/flowcommunity-ark/NextGenPlugins` is an operator-provided local clone of popular
ArkApi/Windows plugin sources for future Obelisk Plugin Hub planning.

Use this material only as a names and demand dictionary. Do not copy Windows ArkApi code,
offsets, MSVC ABI assumptions, vtables, memory layouts, direct UE pointer API patterns,
constants, schemas, control flow, command parsers, or implementation details into Obelisk.

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

Quick local filename scan result, excluding `.git` metadata: the cloned plugin area
currently exposes 834 C/C++ source/header plus readme/license-like files. If project
metadata such as JSON, solution, and Visual Studio project files is included, the count is
higher; use the narrower 834 figure for reproducible demand inventory checks. Visible
ArkApi-facing filenames and plugin families point to chat, console, and RCON command
registration; timer callbacks; hook-heavy gameplay integrations; world/actor traversal;
chat/server messages; permissions; and save/respawn/build/damage-style demand.
`StructuresLimit`, `SafeZone`, and `NoCollision` reinforce demand for a future structure
build-placement policy lane, but they do not promote `APrimalStructure.IsAllowedToBuild`
or any return-code semantics today.

Use this clone as a names/demand dictionary, not as source code to port.
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

## v1 Planning Clarification

The next high-value Plugin Hub clarification is production-readiness criteria for the
current safe seed classes, not another demand category from this inventory.

For v1 planning, split work into two lanes:

- Production Plugin Hub lane: lifecycle/config/logging, descriptor readers,
  and process-local timers. This lane can improve docs, examples, packaging, capability
  checks, fail-closed config, shutdown cleanup, and multi-instance-safe file layout
  without adding new SDK symbols.
- Experimental seed lane: `oChatLogger`, `oChatAudit`, and `oPolicyAudit` may teach
  copied chat/policy audit patterns, but they are not production Plugin Hub modules and
  do not promise that copied chat or policy auditing is generally available.
- Evidence/design backlog: permissions/admin, RCON, economy, homes/safe zones, broadcasts,
  structure enforcement, inventory/items, dinos, tribes, transfers, and persistence-backed
  services. These remain design notes until copied identity, privacy, storage or ingress,
  mutation/enforcement, and second-source evidence are promoted for each surface.

The first release-facing clarification should define acceptance boundaries for a passive
chat parser/auditor: copied text is callback-scope and local; it does not include sender
identity, command SDK guarantees, replies or send-chat, moderation or blocking,
permissions, operator ingress, or durable cross-event identity. That can define an honest
release-candidate seed boundary while keeping player identity and other dependency work in
the core evidence backlog rather than turning it into a public API promise.

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
2. Passive chat parsing and plugin-local text routing on top of copied `ChatMessageEvent`,
   without claiming a command, moderation, or reply/send-chat SDK.
3. Permissions/admin only after copied identity and privacy-safe grants/checks; do not use
   public `ResourceHandle` or UE pointers.
4. RCON/operator I/O only after secret-safe ingress, audit policy, and lifecycle rules.
5. Basic economy/rewards only after plugin-local text routing or a future promoted command
   surface, permissions, identity, and persistence are promoted, and still before any
   give-item or mutation surface.
6. Homes/safe zones/structures only after location, ownership, enforcement, and mutation
   contracts have their own evidence and promotion records.
7. Items, inventory, dinos, transfers, and missions remain investigation/internal unless
   copied-data, lifecycle, identity/privacy, and promotion gates are complete.

## Boundary Audit

Audit note on 2026-05-30: this note should stay a provenance and demand-pressure record,
not a second status matrix. The capability matrix is the single public-facing status table
for NextGen/AseApi demand categories:
`docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`.

The Plugin Hub docs now give enough contributor guidance for post-`v0.1` seed examples
because the allowed seed classes, non-goals, and evidence gates are explicit in
`docs/PLUGIN_HUB_FOUNDATION_V1.md`, `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`, and
`plugins/README.md`. The current first-party plugin tree already covers the safe
current-ABI classes: release examples for lifecycle, timers, and descriptors, plus
experimental examples for copied chat and copied policy auditing.

Therefore the next honest first-party category is not permissions, economy, RCON, homes,
inventory, dinos, tribes, transfers, structure enforcement, broadcasts, or item mutation.
If counting only release-scope examples, graduate passive copied-chat audit/parser
guidance next; if counting experimental examples too, the honest answer is that no new
category is ready until a new copied-data surface is promoted.
