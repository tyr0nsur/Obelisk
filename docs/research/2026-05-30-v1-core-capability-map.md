# v1 Core Capability Map

## Objective

Define the post-`v0.1.0-rc.2` direction toward a broader production-ready Obelisk core
that can later support ArkApi-style plugin replacement on Linux without exposing UE4
internals or unsafe memory-derived handles.

## Baseline

`v0.1.0-rc.2` is the published core-first RC baseline. It proves the Linux runtime,
ProcessEvent hook infrastructure, plugin lifecycle, install layout, `oBaseEvents`, copied
`GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, metadata-only descriptors, and
process-local owner-token timers.

The RC does not promote public player, tribe, dino, item, inventory, structure, mission,
transfer, admin, command, permission, economy, database, mutation, return override,
UE lookup, or `ResourceHandle` APIs.

## Capability Families

| Family | Current Obelisk surface | v1 core need | Later plugin/module work |
| --- | --- | --- | --- |
| Chat and commands | Minimal copied `ChatMessageEvent` with send mode, local sequence, and copied text. | A command router over copied chat text, owner-token command registrations, permission checks, and safe response path once authority is defined. | Command plugins, aliases, moderation, chat tools. |
| Permissions | No public permission service. | A process-local permission service with stable copied identities when available, config-backed rules, and no pointer-derived IDs. | External sync, admin UI, ArkApi migration helpers. |
| Players | No public player identity or lookup. | Copied online-player identity and lifecycle events only after evidence proves stable IDs, privacy boundaries, and fail-closed lookup semantics. | Welcome, stats, moderation, kits, player tools. |
| Tribes | No public tribe API. | Not required for the first v1 core unless needed by permissions/ownership; promote only copied IDs/names after evidence. | Tribe logs, claims, governance. |
| Dinos | No public dino API. | Keep out of the core until identity/lifecycle evidence is stronger. | Breeding, limits, tracking. |
| Items and inventory | Inventory-backed policy checks through `GameplayPolicyEvent`; no item identity or mutation. | Continue copied policy events and descriptors; keep item identity, `ItemNetID`, arrays, mutation, and `ResourceHandle` blocked. | Kits, shops, stacks, inventory tools. |
| Structures | Structure-backed policy checks through `GameplayPolicyEvent`; no structure identity or lookup. | Consolidate copied policy events and descriptors; defer full structure identity, coordinates, health, inventory, and mutation. | Protection, limits, logging, decay. |
| Timers | Process-local owner-token scheduler with zero-failure handles, one-shot/repeating callbacks, explicit unregister, and unload/init-failure cleanup. | Harden examples/docs and keep timers independent of UE4, identity, and shared-cluster state. | Timed plugin tasks, cron-like plugins. |
| Admin | No gameplay admin API. | Keep core to operator/config/logging primitives until player identity and authority model exist. | Kick/ban/broadcast panels and automation. |
| Economy/database | No core surface. | Do not include in v1 core unless a generic storage abstraction is separately designed and lifecycle-tested. | Economy, shop, rewards, MySQL-backed plugins. |

## Breadth Guardrail

The v1 route must not narrow into only chat helpers, `ResourceHandle` revalidation, or
`APrimalStructure.IsAllowedToBuild` triage. Those are useful evidence lanes, but the
planning map stays organized around the broader modding surface: players, tribes, dinos,
items, structures, permissions, commands, admin, transfers, missions, timers, and storage.

This breadth is a discovery and prioritization guardrail, not a delivery promise. A family
can appear in the map as demand or future module work while still having no public SDK,
identity, lookup, mutation, return override, or handle contract.

## Core v1 Principles

- Public ABI remains C/POD, append-only, owner-token scoped, and capability-discovered.
- Stable APIs expose copied Obelisk-owned data, not `UObject*`, `UFunction*`, `FString`,
  raw params, FName/GObjects indices, or memory-derived handles.
- ArkServerApi/AseApi is a compatibility dictionary only. Use its names and behavior
  taxonomy to seed candidate discovery, then rederive every `UFunction`/`UProperty`
  through Obelisk reflection snapshots, second-source gates, and Linux ProcessEvent copied
  data. Do not copy its offsets, vtables, layouts, MSVC conventions, Windows libraries, or
  direct field/native-call wrappers.
- Each module promotion needs accepted target-set evidence, second-source/static support,
  lifecycle cleanup, privacy rules, and tests that prove no mutation or return override is
  implied unless explicitly promoted.
- ArkApi compatibility should be rebuilt as plugins and module APIs on top of Obelisk
  primitives, not by cloning unsafe raw UE pointer surfaces.

## Next Work

1. Do not spend time on broad FName/GObjects/UFunction scans for the current ARK binary
   hash while the accepted root/target-set evidence remains coherent. Use closed target
   sets and small provenance-gated artifacts instead.
2. Clear the highest-value blocker for future identity/lookup work: regenerate or verify
   the small UObject flag-policy provenance sidecars needed for consume-mode indexing,
   while keeping `ResourceHandle`, public GObjects, mutation, and return override blocked.
3. Keep Item return-only, Mission copied-bool, and Transfer `bAccept` as internal/test-only
   copied-scalar slices until separate runtime, dispatcher lifecycle, ABI, and privacy
   gates exist.
4. Validate the first non-UE-dependent core service end to end: owner-token
   process-local timers now have ABI, runtime, unload cleanup, init-failure cleanup, and
   first-party `oProcessTimer` example coverage. Keep timers independent of identity,
   permissions, command routing, UE/gameplay timers, and shared-cluster state.
5. Keep server-backed validation behind explicit live-ops windows; prefer offline
   artifacts and fixture-backed tests until a concrete runtime signal is required.
6. After descriptor/smoke coverage, Transfer bool-tail refresh, and Item return-only
   lifecycle work are closed, the next broad v1 discovery family should be
   `players_identity_lifecycle`: build a closed offline target set around
   `ShooterPlayerController`/`PlayerState` login and lifecycle names, classify only
   copied/redacted fields, and keep `ResourceHandle`, lookup, UE pointers, mutation,
   return override, and runtime work out of scope until a separate gate exists. The first
   docs-only plan is
   [2026-05-30-player-identity-lifecycle-plan.md](2026-05-30-player-identity-lifecycle-plan.md);
   it is candidate-only and does not promote a player SDK.
