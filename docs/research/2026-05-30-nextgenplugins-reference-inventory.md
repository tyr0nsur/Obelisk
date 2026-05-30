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

Do not let this inventory pull internal evidence lanes into Plugin Hub scope prematurely.
For example, Transfer remains an internal evidence backlog item unless a concrete plugin
family creates demand for a public Transfer surface and the Obelisk promotion gates are
met. The current high-demand families are permissions/admin, economy/shop/rewards, chat
commands, homes/teleport/safe-zone, RCON/operator integration, structures, dinos, tribes,
and lifecycle/crash handling.
