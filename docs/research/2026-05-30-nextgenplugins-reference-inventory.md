# NextGenPlugins Reference Inventory

Date: 2026-05-30

## Scope

`/home/flowcommunity-ark/NextGenPlugins` is an operator-provided local clone of popular
ArkApi/Windows plugin sources for future Obelisk Plugin Hub planning.

Use this material only as a behavior and feature-priority reference. Do not copy Windows
ArkApi code, offsets, MSVC ABI assumptions, vtables, memory layouts, direct UE pointer API
patterns, or implementation details into Obelisk.

## Local Inventory

Top-level collections:

- `/home/flowcommunity-ark/NextGenPlugins/Michidu-Ark-Server-Plugins`
- `/home/flowcommunity-ark/NextGenPlugins/ASE-Plugins`

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
initialized in this local copy. The visible top-level license is MIT, but individual
submodules/plugins must still be checked before any derived documentation or compatibility
claim.

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

## Constraints

- Keep the current Obelisk core route first: copied events, stable C ABI, owner-token
  lifecycle, descriptor metadata, no UE internals in public plugin APIs.
- Treat ArkApi plugin source as a feature dictionary only.
- Any future Obelisk Plugin Hub compatibility note must describe behavior at a high level,
  not copy implementation.
- Public APIs needed by these plugin families still require Obelisk promotion gates:
  copied payloads, second-source evidence where relevant, ABI tests, privacy policy,
  lifecycle cleanup, and no identity/mutation/return override unless explicitly promoted.

## Recommendation

Keep this local clone out of the Obelisk repository and use it later to build a
`Plugin Hub compatibility matrix` once the v0.1 stable core is ready. The first useful
matrix should list plugin name, feature category, required Obelisk API surface, current
Obelisk readiness, and blocked capabilities.

Do not convert this into a public compatibility promise yet. The matrix should stay in
`docs/research/` until the v1 core has stable copied surfaces, lifecycle cleanup,
multi-instance config, and secret-safe DB/webhook/RCON patterns.

Do not let this inventory pull internal evidence lanes into Plugin Hub scope prematurely.
For example, Transfer remains an internal evidence backlog item unless a concrete plugin
family creates demand for a public Transfer surface and the Obelisk promotion gates are
met. The current high-demand families are permissions/admin, economy/shop/rewards, chat
commands, homes/teleport/safe-zone, RCON/operator integration, structures, dinos, tribes,
and lifecycle/crash handling.

Recommended v1 ordering from this demand inventory:

1. Hub foundation: lifecycle, descriptors, timers, config/logging, reload posture, and
   multi-instance-safe packaging.
2. Chat commands on top of copied `ChatMessageEvent`, without claiming a moderation or
   reply/send-chat SDK yet.
3. Permissions/admin with copied identity and privacy-safe grants/checks; do not use
   public `ResourceHandle` or UE pointers.
4. RCON/operator I/O and secret-safe configuration.
5. Basic economy/rewards that depend on commands, permissions, identity, and persistence,
   before any give-item or mutation surface.
6. Homes/safe zones/structures after location, ownership, enforcement, and mutation
   contracts are promoted.
7. Items, inventory, dinos, transfers, and missions remain investigation/internal until
   copied-data, lifecycle, identity/privacy, and promotion gates are complete.
