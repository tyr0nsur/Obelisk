# Plugins

This directory contains first-party Obelisk plugins.

Read [../docs/PLUGIN_ARCHITECTURE.md](../docs/PLUGIN_ARCHITECTURE.md) before adding a new
plugin.

Creator-facing examples that build against an installed SDK package live in
[`../examples`](../examples). The plugins in this directory are first-party in-tree
reference plugins and may use repository-local test/build wiring.

## First-Party Plugins

```text
plugins/
  oBaseEvents/    Official example plugin for events, config, ABI checks, and shutdown.
  oProcessTimer/  Official core example plugin for process-local Obelisk timers.
  oDescriptorCatalog/
                  Official metadata-only example for descriptor discovery.
```

`oBaseEvents` is the baseline public event example from the current RC scope. It should
remain small and instructional: it exists to show contributors how to build their own
Obelisk plugin, not to become a feature-heavy server plugin.

`oProcessTimer` is part of the first-stable core plugin set for `v0.1.0`. It demonstrates
only the process-local timer ABI: owner-token registration, zero-failure handles, and
explicit unregister on shutdown. Timer unregister cancels future delivery, but it is not a
callback quiescence proof for heap-owned `user_data`; examples must keep timer state valid
until their own synchronization or Obelisk owner cleanup proves callbacks are no longer in
flight. It is not a gameplay/module timer abstraction and does not use UE timers, gameplay
timers, UE identity, lookup, permissions, commands, shared scheduler state, persistent
handles, or cluster coordination.

`oDescriptorCatalog` is the post-RC reference plugin for descriptor discovery and the next
release-scope metadata example. It reads `DescribeResourceKind` and
`DescribeGameplayPolicyEventKind`, validates routing metadata, and logs sanitized
category/event summaries. It does not register callbacks, timers, threads, chat handlers,
HTTP endpoints, resource identities, lookups, mutations, return overrides, or raw
`ProcessEvent` access.

## Adding Creator-Facing Examples

Plugin Hub work is post-SDK-complete planning only. Do not add new first-party Plugin Hub
seed examples while the complete-SDK blockers remain open. The parked release-supported
additions after `v0.1` are descriptor readers and process-local timer utilities. Passive
copied-chat parsers and copied policy auditors are experimental pattern examples only. The
current tree already has examples for both buckets, so treat new first-party work as a
promotion review or refinement of the existing examples unless a separate copied-data
surface has passed the capability-matrix evidence gate.

If an example request is motivated by ArkApi, AseApi, NextGenPlugins, or another
popular-plugin family, treat that input as names and demand signals only. It is not an
architecture source, ergonomics source, compatibility target, source reference, ABI
reference, schema, command parser, or implementation pattern.

Do not add a first-party example that implies commands, permissions, economy, homes, RCON,
storage/database services, webhooks, inventory/item mutation, dino tools, tribe tools,
transfer handling, structure placement enforcement, identity, lookup, replies, send-chat,
moderation, or ArkApi portability until the matching public surface is promoted in the
public ABI, recorded in the capability matrix, and documented with its own evidence gate.

Release-supported seed examples are limited to lifecycle/config/logging, descriptor
readers, and process-local timer utilities. Those release-supported seeds still must
keep the shared safe default config posture (`enabled=false`, `allow_all_instances=false`,
and an empty `instance_allowlist`), fail closed on missing capabilities or callbacks,
validate instance scoping, unregister owner-token handles on every shutdown or
partial-init path, treat callback payloads as callback-scope, keep mutable state
process-local unless a locking model is documented, and log only bounded, sanitized
output.

Passive copied-chat parser or audit examples must add one stricter rule: copied chat text
is local routing input only. They may count, bucket, redact, or parse text in memory, but
must not persist raw player text, expose sender/player identity, claim command SDK
semantics, reply or send chat, block or moderate chat, perform permission checks, bridge
operator ingress, correlate events into durable identity, or use raw UE/`ProcessEvent`
data to fill those gaps.

## Experimental Examples

`oPolicyAudit` demonstrates the promoted `GameplayPolicyEvent` callback family without
touching `ProcessEvent`, UE internals, object identity, or pointer-derived data.
`oChatLogger` demonstrates the minimal copied `ChatMessageEvent` surface by logging only
event metadata and copied message size, not player identity or raw chat payload text.
`oChatAudit` combines the copied `ChatMessageEvent` surface with process-local
owner-token timers to emit a bounded periodic digest of chat counts, send modes, and
message-size buckets. It does not log raw chat text, player/sender identity, UE pointers,
commands, permissions, moderation decisions, mutations, replies, persistent handles, or
cross-process/cluster audit state.
These examples observe copied data only; they are not policy enforcement, command/chat
authority, storage/webhook, or public module SDK examples.
Their default configs are safe-disabled and cluster-scoped. They are not part of the first
release scope or the default top-level build; build them only when explicitly investigating
experimental examples:

```bash
cmake -S . -B build -DOBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON
cmake --build build --target oPolicyAudit oChatLogger oChatAudit -j"$(nproc)"
```

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "policy_audit": {
    "enabled": false,
    "event_kind_mask": 255,
    "log_limit": 10
  }
}
```

`oChatLogger` config:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
```

`oChatLogger` logs a bounded first set per chat send mode, currently up to sixteen accepted
events for each mode `0..3`. It records only sequence, send mode, copied-payload flag,
message size, per-mode count, and first-observed status; it does not log raw chat text,
sender identity, or UE pointers.
When disabled by config, it requires only the base ABI prefix and owner token and does not
register a chat callback. Active config requires the public chat-event capability, matching
appended API slots via `struct_size`, and non-null chat registration functions.

`oChatAudit` config:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "chat_audit": {
    "enabled": false,
    "digest_interval_ms": 60000,
    "log_on_shutdown": true,
    "max_message_size_bucket": 4096
  }
}
```

When active, `oChatAudit` requires the public chat-event capability, timer capability,
matching appended API slots via `struct_size`, non-null registration functions, and a
non-zero owner token. It registers exactly one chat callback and one repeating timer, then
unregisters the timer before the chat callback during shutdown. Digest output is
process-local metadata only: accepted/malformed event counts, per-mode counts, total and
max byte sizes, bounded size buckets, and overflow count.
When disabled by config, discovery/init should require only the base ABI prefix and owner
token; optional chat/timer slots are required only before registering active callbacks.

## Policy

- Plugins activate only when their `.so` is published into the runtime `plugins/`
  directory. Use `scripts/install_obelisk_plugin.sh` instead of copying directly into the
  active directory, so shared clusters never discover a partial `.so`. In a clustered
  install that directory can be shared by every ARK instance, so use `instance_allowlist`
  for targeted rollout. `enabled=true` with an empty allowlist stays skipped unless
  `allow_all_instances=true` is set explicitly.
- Stable plugins must use runtime-owned central config paths:
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- Treat multi-instance loading as the default cluster shape. A plugin may read shared
  config from every ARK process, but mutable plugin state should be stored per
  `OBELISK_INSTANCE_ID` unless the plugin has a documented cross-process locking model.
- Prefer copied Obelisk-level events. Filtered and global raw `ProcessEvent` callbacks
  require explicit debug gates and isolated validation.
- Long-lived callbacks should use owner-token handle registration and explicit unregister
  during shutdown; registration handles are process-local, not shared cluster state.
- Plugins that start HTTP servers, threads, or file readers need a documented shutdown
  design before they can be stable.
