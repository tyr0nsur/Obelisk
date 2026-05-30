# v1 Core Capability Map

## Objective

Define the post-`v0.1.0-rc.1` direction toward a broader production-ready Obelisk core
that can later support ArkApi-style plugin replacement on Linux without exposing UE4
internals or unsafe memory-derived handles.

## Baseline

`v0.1.0-rc.1` is the published core-first RC baseline. It proves the Linux runtime,
ProcessEvent hook infrastructure, plugin lifecycle, install layout, `oBaseEvents`, copied
`GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, and metadata-only descriptors.

The RC does not promote public player, tribe, dino, item, inventory, structure, mission,
transfer, admin, command, permission, timer, economy, database, mutation, return override,
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
| Timers | No public scheduler. | Add a process-local scheduler with owner-token handles, unregister on unload, and no shared-cluster handle persistence. | Timed plugin tasks, cron-like plugins. |
| Admin | No gameplay admin API. | Keep core to operator/config/logging primitives until player identity and authority model exist. | Kick/ban/broadcast panels and automation. |
| Economy/database | No core surface. | Do not include in v1 core unless a generic storage abstraction is separately designed and lifecycle-tested. | Economy, shop, rewards, MySQL-backed plugins. |

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

1. Harden the target-set evidence contract so accepted readiness reports are explicitly
   `gate_mode=second_source_promotion`, name at least one target set, and remain
   layout-only with `promotion_ready=false` until a separate API/runtime promotion gate
   exists.
2. Continue focused UE4 reflection extraction for GObjects coherent-field-window evidence
   and Item return-only policy modeling first, with Mission copied-bool and Transfer
   `bAccept` kept as internal/test-only follow-up candidates.
3. Design the first non-UE-dependent core service: an owner-token process-local scheduler
   with unload cleanup tests, before identity, permissions, and command routing.
4. Keep server-backed validation behind explicit live-ops windows; prefer offline
   artifacts and fixture-backed tests until a concrete runtime signal is required.
