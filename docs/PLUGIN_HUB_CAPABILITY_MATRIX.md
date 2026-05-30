# Plugin Hub Capability Matrix

This matrix is a contributor-facing planning aid for future Obelisk Plugin Hub work. It
maps common modder intents to the public Obelisk surface that is safe today.

It is not a compatibility promise for ArkApi plugins, not a module SDK roadmap freeze, and
not a replacement for promotion gates. If a row says "not ready", plugins must not work
around the gap with raw UE pointers, `ProcessEvent` mutation, object lookup, or copied
ArkApi implementation patterns.

The local `NextGenPlugins` clones are useful as a demand map for future Plugin Hub
categories, not as portable implementation source. Treat their plugin families as evidence
of operator needs, then rebuild every promoted surface through Obelisk reflection,
second-source fixtures, copied C ABI contracts, and runtime safety gates.

| Modder intent | Use now | Status | Must not imply |
| --- | --- | --- | --- |
| Load a Linux-native plugin | `ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init`, optional `ObeliskPlugin_Shutdown` | Stable baseline | Hot reload of Obelisk itself, detached workers, or background ingress without shutdown proof |
| Log through Obelisk | `ObeliskPluginInitContext::Log` after `struct_size` checks | Stable baseline | Long-lived ownership of callback data or cross-thread logging contracts not proven by the plugin |
| Discover resource categories | `DescribeResourceKind` | Promoted metadata | Resource identity, object lookup, persistent handles, or correlation between events |
| Discover promoted policy event kinds | `DescribeGameplayPolicyEventKind` | Promoted metadata | Complete gameplay inventory, public module SDK, mutation path, or return override |
| Observe promoted structure/item policy data | `GameplayPolicyEvent` with owner-token registration | Promoted v0.1 SDK surface | Public `StructureEvents`, Inventory SDK, Items SDK, UE pointers, player/item/structure identity, mutation, or return override |
| Parse copied chat text locally | `ChatMessageEvent` with owner-token registration | Minimal v0.1-rc ABI surface | Command SDK, sender identity, replies, moderation, chat blocking, or send-chat API |
| Run process-local scheduled work | Owner-token timers | Promoted v0.1 core primitive | UE/gameplay timers, cluster scheduler, persistent ids, permission system, or command router |
| Inspect descriptor output safely | `oDescriptorCatalog` | First-party metadata example | Resource discovery, callback subscription, identity, lookup, mutation, or return override |
| Build simple lifecycle/config examples | `oBaseEvents`, `oProcessTimer`, descriptor examples | Reference plugins | Gameplay authority, module SDK coverage, or ArkApi plugin portability |
| Use raw `ProcessEvent` callbacks | Filtered callbacks behind explicit debug gates | Debug-gated runtime plumbing | Stable gameplay API, borrowed pointer lifetime, raw param API, or public Plugin Hub dependency |
| Commands, permissions, economy, kits, shops, RCON | No public Obelisk SDK yet | Not ready | ArkApi compatibility, player identity, reply/send-chat, database service, or operator command lifecycle |
| Inventory/item identity and mutation | No public Obelisk SDK yet | Not ready | `ResourceHandle`, `ItemNetID`, inventory lookup, item mutation, give/remove item, or return override |
| Players, tribes, dinos, missions, transfers | No public Obelisk SDK yet | Not ready | Public identity, ownership lookup, mutation, teleport/spawn APIs, transfer payload decoding, or cross-map correlation |
| Structure census/proximity | No public Obelisk SDK yet | Not ready | Public GObjects traversal, structure handles, exact coordinates, ownership lookup, linked-structure traversal, or mutation |
| Structure build placement policy | No public Obelisk SDK yet | Not ready | `APrimalStructure.IsAllowedToBuild` compatibility, placement denial, no-collision behavior, structure identity, location disclosure, mutation, or return override |

## Current Safe Route

For plugin authors, the stable v0.1.x shape is descriptor-driven:

1. Check `abi_version`, `struct_size`, capability bits, and function pointers.
2. Use `DescribeResourceKind` to discover promoted categories.
3. Use `DescribeGameplayPolicyEventKind` to discover promoted copied policy kinds.
4. Subscribe only to promoted copied events with owner-token handles.
5. Route by copied `resource_kind`, `event_kind`, and `field_mask`.

Plugins must copy any callback data they need after the callback returns. Runtime-owned
event data is callback-scope only.

## Plugin Hub Direction

The first useful Plugin Hub categories should be built from surfaces that already exist:

- lifecycle/config/logging examples;
- descriptor/catalog consumers;
- copied `GameplayPolicyEvent` auditors;
- copied `ChatMessageEvent` parsers that do not claim identity, replies, moderation, or a
  command SDK;
- process-local timer utilities.

Higher-level ArkApi-style families such as permissions, economy, kits, homes, safe zones,
RCON, inventory tools, dino tools, tribe tools, and build-placement policy remain future
work. Each requires its own copied-data evidence, ABI design, privacy policy, lifecycle
tests, and promotion gate.

The safest future structure direction is likely aggregate/census-style data, such as
counts by copied category or bounded proximity signals, because it can be designed without
public structure handles. It still needs a separate design that avoids public GObjects
traversal, exact coordinates, ownership lookup, linked-structure traversal, mutation, and
cross-event identity claims.
