# Plugin Hub Foundation V1

Plugin Hub Foundation V1 is the minimum contributor-facing contract for Linux-native
Obelisk plugins that consume `include/obelisk/ObeliskApi.h`.

It is a boundary document, not a roadmap freeze. It does not add public symbols, structs,
callbacks, capabilities, or gameplay modules. It does not promise ArkApi/AseApi
compatibility, Windows/MSVC portability, source parity, or behavior parity. ArkApi,
AseApi, and local popular-plugin clones are names and demand dictionaries only, not
porting or copying sources; every Obelisk surface must be rebuilt through Obelisk
reflection, copied C ABI contracts, second-source fixtures, and runtime safety gates.

This foundation is a post-RC contributor seed for the current ABI, not a change to the
published `v0.1.0-rc.2` tag. It explains what small native examples can honestly teach
while module lanes such as commands, permissions, inventory, structures, players,
missions, and transfers remain planning-only until separately promoted.

## Public Surface

Foundation V1 contains only the public ABI already exposed by `ObeliskApi.h`:

- `ObeliskPlugin_GetInfo`
- `ObeliskPlugin_Init`
- optional `ObeliskPlugin_Shutdown`
- Obelisk logging callbacks
- plugin metadata, config directory, and init context
- metadata-only descriptors through `DescribeResourceKind`
- metadata-only descriptors through `DescribeGameplayPolicyEventKind`
- copied `GameplayPolicyEvent` observers
- minimal copied `ChatMessageEvent` observers
- owner-token, process-local timers
- raw `ProcessEvent` callbacks only as debug-gated runtime plumbing, not as Plugin Hub API

Plugins should use `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md` to decide which intents are safe
today. If an intent is marked "not ready", a plugin must not fill the gap with raw UE
pointers, GObjects traversal, raw params, return overrides, mutation, or copied ArkApi
implementation patterns.

## C ABI Contract

The ABI is C, append-only, and capability-gated:

- cross-boundary data is POD with explicit integer widths;
- strings are pointer-plus-size views and callback-scope unless documented otherwise;
- callbacks use function pointers and opaque user data;
- public structs are versioned by `abi_version` and bounded by `struct_size`;
- optional calls require the capability bit, sufficient `struct_size`, and a non-null
  function pointer;
- fields may be appended, but existing field order and meaning must not change within ABI
  v1;
- `ObeliskApi*` and `ObeliskPluginInitContext*` are borrowed during initialization.

Do not pass STL types, C++ exceptions, references, classes, RTTI-owned objects, UE types,
or raw game memory across the plugin ABI.

## Lifecycle And Ownership

`Init` must fail closed when required capabilities, config, or callbacks are unavailable.
Any callback or timer registration must use a non-null owner token. Registration returns
handle `0` on failure. Unregistration must use the same owner token.

Plugins must clean up registrations after partial initialization failure and during
shutdown. Shutdown must be idempotent because the runtime may call it while unloading
after earlier failures. Individual unregister calls cancel future delivery but are not a
quiescence barrier for every callback family. The runtime owner cleanup performed during
plugin unload is the barrier before plugin code and owner state are finally released, so a
plugin must not free callback-owned state until its own shutdown path has made that state
unreachable to callbacks it still owns.

Event payloads are callback-scope. A plugin that needs data after the callback returns
must copy it into plugin-owned storage.

## Config Baseline

First-party examples use the same safe default posture:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
```

Plugin config belongs under `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`. Instance
tokens must be validated as safe path components. Runtime handles, owner tokens, callback
handles, timer ids, and event sequence values are process-local and must not be persisted
or shared across maps, processes, or clusters.

## Safe Uses Now

Foundation V1 is enough for small, honest Plugin Hub seeds:

- lifecycle, config, and logging examples;
- descriptor/catalog readers;
- copied `GameplayPolicyEvent` auditors;
- copied `ChatMessageEvent` text parsers without sender identity, replies, moderation, or
  a command SDK;
- process-local timer utilities.

These examples may demonstrate patterns, but they are not promises for complete economy,
permissions, homes, kits, shops, RCON, inventory, item, dino, tribe, mission, transfer, or
structure modules.

## Fastest Honest Creator Path

After `v0.1`, the fastest useful path for plugin creators is to build narrow
Obelisk-native examples in this order:

1. Start from lifecycle, config, logging, and `struct_size`/capability checks.
2. Add descriptor reads so plugins can explain which copied event categories are actually
   promoted.
3. Add passive copied chat parsing for local text routing only, with no sender identity,
   replies, moderation, blocking, or send-chat behavior.
4. Add process-local timers only for plugin-owned periodic work, never as gameplay timers,
   persistent ids, or cluster coordination.
5. Add copied policy auditors that observe promoted `GameplayPolicyEvent` data without
   identity, lookup, mutation, return override, or module SDK claims.

If a plugin idea needs player identity, permissions, persistence, operator ingress,
replies, broadcast, inventory/item mutation, teleport, structure placement enforcement, or
raw UE access, it is not a Foundation V1 plugin. Keep it as a design/research note until a
separate copied-data surface is promoted.

## Anti-Promises

Foundation V1 does not provide or imply:

- ArkApi/AseApi binary, source, or behavior compatibility;
- Windows/MSVC plugin portability;
- `ResourceHandle`, object identity, resource identity, player identity, tribe identity,
  item identity, inventory identity, structure identity, lookup, or cross-event
  correlation;
- public Inventory SDK, Items SDK, StructureEvents SDK, command SDK, permissions,
  economy, kits, shops, homes, teleport, safe zones, RCON, replies, send-chat, or
  moderation;
- gameplay mutation, inventory mutation, item grants/removal, dino spawn/mutation,
  structure placement denial, no-collision behavior, or return override authority;
- stable raw `ProcessEvent`, raw UE pointers, raw params, FName indices, GObjects indices,
  `UObject`, `UFunction`, or `FString` access as Plugin Hub API;
- persistent or cross-cluster handles, owner tokens, timers, callback handles, or
  sequences.

## Evidence Gate

Promoting any new Plugin Hub surface requires a separate design and evidence trail:

- copied-data ABI shape with ownership and privacy rules;
- second-source fixtures or accepted runtime evidence for the target;
- fail-closed config and lifecycle tests;
- SDK consumer tests for C and C++;
- public docs that state both the safe use and the non-goals;
- guardrails that keep unpromoted identity, lookup, mutation, and return overrides out of
  the public SDK.
