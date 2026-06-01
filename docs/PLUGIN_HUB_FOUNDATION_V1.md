# Plugin Hub Foundation V1

Status: post-SDK-complete planning only.

Read `PLUGIN_HUB_SEED_BOUNDARY.md` first: Plugin Hub seeds are not evidence that the
Obelisk v1 SDK is complete.

Plugin Hub Foundation V1 is a deferred contributor-facing seed contract for Linux-native
Obelisk plugins that consume `include/obelisk/ObeliskApi.h`. In this document, `V1`
means the first reviewed Plugin Hub foundation/intake contract revision. It is not
Obelisk SDK v1, not `v1.0 stable`, and not a Plugin Hub completion claim.
Do not treat this document as active roadmap work while the complete SDK blocker chain
remains open. Current engineering priority is the SDK itself.

It is a boundary document, not a roadmap freeze. It does not add public symbols, structs,
callbacks, capabilities, or gameplay modules. More specifically, it does not add public
contract structs/events/descriptors/API tables. It does not promise ArkApi/AseApi
compatibility, Windows/MSVC portability, source parity, behavior parity, or direct plugin
portability. ArkApi, AseApi, and local NextGenPlugins clones are names and demand signals
only for support-tier decisions. They are not architecture, ergonomics, behavior, porting,
implementation, or copying sources. Every Obelisk surface must be rebuilt through Obelisk
reflection, copied C ABI contracts, explicitly named second-source target sets, and runtime
safety gates.

This foundation is post-SDK planning, not a change to the published `v0.1.0-rc.2` tag.
It records what future native examples may honestly teach after the SDK blocker chain is
closed. It must not compete with current work on players, commands, permissions,
inventory, structures, missions, transfers, storage services, or other SDK surfaces.

When Plugin Hub resumes after SDK completion, release-supported seed work can start with
lifecycle/config/logging skeletons, descriptor/catalog consumers, and process-local timer
utilities that use the public C ABI with fail-closed capability checks. Copied `ChatMessageEvent` parsing and copied
`GameplayPolicyEvent` auditing remain experimental seed patterns only; they are not
production Plugin Hub modules, command/chat SDKs, policy-enforcement SDKs, or evidence of
a new ABI. They are also not public command SDK/router surfaces, replies, permissions,
identity, send-chat, or moderation.

For future Plugin Hub release notes, package READMEs, and contributor reviews, the seed
set should start from lifecycle/config/logging plugin skeletons, descriptor/catalog readers, and
process-local timer utilities. Passive copied chat parsing and copied policy auditing are
experimental examples only. Permissions/admin, commands/replies/send-chat/broadcast,
economy, kits, homes, teleport, and item grants stay blocked until the required
identity/principal, permissions/admin, command routing, response path,
persistence/storage, and safe mutation/grant surfaces are separately promoted.

Creator-facing examples that build against an installed SDK package live under
`examples/`; `examples/sdk_minimal_plugin` is the starter seed for an installed SDK
consumer, `examples/sdk_descriptor_catalog` demonstrates descriptor/catalog reads, and
`examples/sdk_timer_plugin` demonstrates the promoted process-local timer surface using
only the installed package. `examples/sdk_inventory_policy_audit` demonstrates an
experimental copied `GameplayPolicyEvent` audit pattern for inventory-backed event
categories only; it is not release-supported and does not add inventory/item identity,
lookup, mutation, return override, command, permission, send-chat, storage, or
compatibility surface. First-party runtime reference plugins live under
`plugins/` and may use repository-local build/test wiring, so they are reference plugins
in-tree rather than the starter installed-SDK consumer contract.

The current release-supported installed-SDK templates are exactly the starter template
(`examples/sdk_minimal_plugin`), descriptor catalog template
(`examples/sdk_descriptor_catalog`), and owner-token timer template
(`examples/sdk_timer_plugin`). They teach package shape, installed-SDK CMake use,
safe-disabled config posture, public C ABI checks, metadata-only descriptor reads, and
process-local owner-token timer cleanup. They do not promise identity/principal,
permissions/admin, command routing, replies/send-chat/broadcast, storage, inventory/item
or structure modules, mutation, return overrides, cross-process scheduling,
ArkApi/AseApi portability, or SDK v1 completion.

Use `PLUGIN_HUB_CONTRIBUTOR_PATH.md` as the short contributor path for deciding the
support tier, copying the closest installed-SDK example, validating package hygiene,
recording package metadata, and knowing when to stop.

External Plugin Hub examples should request the installed SDK component explicitly with
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and link only
`Obelisk::obelisk_sdk`.

## Package Contract

The pre-v1 Plugin Hub package contract is an intake boundary for examples and future
publisher tooling. It is not a registry implementation, a machine-readable manifest
schema, a compatibility promise, or v1 completion evidence.

A candidate package should contain one Linux shared object, a README, license text, and a
config example or schema when the plugin reads config. The package metadata must be
explicit enough for review: `plugin_id`, display name, plugin version, minimum Obelisk SDK
line, exactly one `Support tier: <tier>` declaration using release-supported seed,
experimental pattern, or blocked backlog, used capabilities, config path, exported ABI
entry points, and whether shutdown is exported and why.
Directory index files such as `examples/README.md` may summarize tiers, but they are not
package metadata; each candidate package README or manifest owns the single reviewed
`Support tier:` declaration.

Review must fail if README, package metadata, or public seed docs claim v1 readiness,
ArkApi/AseApi compatibility, commands, permissions, identity, send-chat/replies, mutation,
storage, inventory, or structure support outside that one declared tier.

Acceptance for a release-supported seed requires building against an installed SDK with
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`, linking only
`Obelisk::obelisk_sdk`, hidden default symbol visibility, no private Obelisk headers, no
raw UE pointers or ArkApi implementation patterns, fail-closed `struct_size` and
capability checks, safe-disabled config defaults, owner-token cleanup, and idempotent
shutdown. Experimental pattern packages must meet the same package hygiene but must be
clearly labeled as experimental and must not imply production command, chat, policy,
inventory, structure, identity, mutation, or enforcement support.

Reject or keep in backlog any package that depends on unpromoted gameplay surfaces,
private runtime headers, raw `ProcessEvent` params, persistent handles, cross-instance
runtime state, send-chat/replies, permissions, identity, storage services, mutation, or
return overrides.

## Public Surface

Foundation V1 contains only the public ABI already exposed by `ObeliskApi.h`:

- `ObeliskPlugin_GetInfo`
- `ObeliskPlugin_Init`
- optional `ObeliskPlugin_Shutdown`
- Obelisk logging callbacks
- plugin metadata, config directory, and init context
- metadata-only descriptors through `DescribeResourceKind`
- metadata-only descriptors through `DescribeGameplayPolicyEventKind`
- copied `GameplayPolicyEvent` observers as experimental pattern examples only for
  target-set-promoted event kinds
- copied notification-only `ChatMessageEvent` observers as experimental pattern examples only
- owner-token, process-local timers
- raw `ProcessEvent` callbacks only as debug-gated runtime plumbing, not as Plugin Hub API

This list names ABI primitives, not Plugin Hub module tiers. Use the support-tier split
below before presenting any example as release-supported, experimental, or blocked.

Plugins should use `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md` to decide which intents are safe
today. If an intent is marked "not ready", a plugin must not fill the gap with raw UE
pointers, GObjects traversal, raw params, return overrides, mutation, or copied ArkApi
implementation patterns.

## Contributor Intake Checklist

Classify every Plugin Hub proposal before writing code:

1. Parked release-supported seed after SDK completion: the future proposal uses only
   lifecycle/config/logging, descriptor/catalog reads, or process-local timers from the
   current C ABI.
2. Experimental pattern only: the proposal passively consumes copied
   `ChatMessageEvent` or `GameplayPolicyEvent` data and clearly avoids identity, lookup,
   public command routing, replies, permissions, moderation, send-chat, enforcement,
   mutation, return overrides, and module SDK claims.
3. Blocked backlog: the proposal needs commands, permissions, persistence, operator
   ingress, send-chat/broadcast, player/tribe/dino/item/structure identity, inventory or
   item mutation, structure enforcement, `ResourceHandle`, raw UE pointers, raw params,
   or cross-instance state.

ArkApi/AseApi/NextGenPlugins demand can justify keeping a blocked idea visible in the
matrix or a research note, but it cannot reclassify that idea as a release-supported seed or
experimental pattern.

## C ABI Contract

The ABI is C, append-only, and capability-gated:

- cross-boundary data is POD with explicit integer widths;
- strings are pointer-plus-size views and callback-scope unless documented otherwise;
- callbacks use function pointers and opaque user data;
- public contract structs/events/descriptors/API tables are versioned by `abi_version`
  and bounded by `struct_size`;
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

Descriptor-only consumers should also export shutdown when they retain process-local
catalog, validation, or logging state. Shutdown should clear that state even when the
consumer never registered callbacks or timers.

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

## Deferred Uses

Foundation V1 defines honest future Plugin Hub seeds after the SDK blocker chain is
closed and support tiers are explicit:

Release-supported seeds:

- lifecycle, config, and logging examples;
- descriptor/catalog readers scaffolded from `examples/sdk_descriptor_catalog`;
- process-local timer utilities.

Experimental pattern examples only:

- copied `GameplayPolicyEvent` auditors for target-set-promoted event kinds named in the
  capability matrix;
- copied `ChatMessageEvent` text parsers without sender identity, replies, moderation, or
  a command SDK; any routing/parsing stays plugin-local only, without permissions,
  send-chat, replies, or a public command SDK/router.

Only lifecycle/config/logging examples, descriptor/catalog readers scaffolded from
`examples/sdk_descriptor_catalog`, and process-local timer examples may become
release-supported seeds after SDK completion. Copied chat parsers and copied policy
auditors may demonstrate patterns, but they remain experimental and are not promises of
complete or partial support for economy, permissions, homes, kits, shops, RCON,
inventory, item, dino, tribe, mission, transfer, storage/database, webhook, or structure
modules.

## Fastest Honest Creator Path

After `v0.1`, the first useful path for plugin creators is to build contributor-ready
Obelisk-native SDK seeds in this order:

1. Start from lifecycle, config, logging, and `struct_size`/capability checks.
2. Add descriptor reads so plugins can explain which copied event categories are actually
   promoted by exact target set.
3. Add process-local timers only for plugin-owned periodic work, never as gameplay timers,
   persistent ids, or cluster coordination.
4. Keep passive copied chat parsing experimental and plugin-local only, with no public
   command SDK/router, sender identity, replies, permissions, moderation, blocking, or
   send-chat behavior.
5. Keep copied policy auditors experimental; they may observe target-set-promoted
   `GameplayPolicyEvent` data without identity, lookup, mutation, return override, or
   module SDK claims.

If a plugin idea needs player identity, permissions, persistence, operator ingress,
replies, broadcast, inventory/item mutation, teleport, structure placement enforcement, or
raw UE access, it is not a Foundation V1 plugin. Keep it as a design/research note until a
separate copied-data surface is promoted.
The same rule applies when the visible feature is framed as permissions/admin,
commands/replies/send-chat/broadcast, economy, kits, homes, teleport, or item grants:
those require promoted identity/principal, permissions/admin, command routing, response
path, persistence/storage, and safe mutation/grant surfaces before they can become release
Plugin Hub examples.
Player identity research is also not unlocked by direct binary/core access: the current
admin snapshot gap requires a reviewed non-protected complete
`obelisk.core-dump-evidence-pack.v1` plus a reviewed UFunction
`obelisk.reflection-inventory-pack.v1` before planning. An offline `ShooterGameServer`
binary or copied core alone is insufficient, and that route still remains candidate-only
rather than Plugin Hub or public SDK evidence.

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
- public permissions/admin checks, command routing, reply path, send-chat/broadcast path,
  economy/kits/homes state, teleport path, or item-grant path without promoted
  identity/principal, permissions/admin, command routing, response path,
  persistence/storage, and safe mutation/grant surfaces;
- no public Mission SDK, Mission module readiness, Mission identity/state mutation, or
  reward/transfer authority from the internal/test-only Mission copied-bool lane;
- public storage SDK, database service, schema/migration contract, secret manager, webhook
  client, or cross-instance persistence API;
- gameplay mutation, inventory mutation, item grants/removal, dino spawn/mutation,
  structure placement denial, no-collision behavior, or return override authority;
- stable raw `ProcessEvent`, raw UE pointers, raw params, FName indices, GObjects indices,
  `UObject`, `UFunction`, or `FString` access as Plugin Hub API;
- persistent or cross-cluster handles, owner tokens, timers, callback handles, or
  sequences.

## Evidence Gate

Promoting any new Plugin Hub surface requires a separate design and evidence trail:

- copied-data ABI shape with ownership and privacy rules;
- explicitly named promoted second-source target sets for the exact gameplay/module
  surface; planning-only, internal-layout, consume-only, or test-only evidence does not
  become public SDK evidence;
- fail-closed config and lifecycle tests;
- SDK consumer tests for C and C++;
- public docs that state both the safe use and the non-goals;
- guardrails that keep unpromoted identity, lookup, mutation, and return overrides out of
  the public SDK.
