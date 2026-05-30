# Plugins

This directory contains first-party Obelisk plugins.

Read [../docs/PLUGIN_ARCHITECTURE.md](../docs/PLUGIN_ARCHITECTURE.md) before adding a new
plugin.

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
explicit unregister on shutdown. It is not a gameplay/module timer abstraction and does not
use UE timers, gameplay timers, UE identity, lookup, permissions, commands, shared
scheduler state, persistent handles, or cluster coordination.

`oDescriptorCatalog` is the post-RC reference plugin for descriptor discovery and the next
release-scope metadata example. It reads `DescribeResourceKind` and
`DescribeGameplayPolicyEventKind`, validates routing metadata, and logs sanitized
category/event summaries. It does not register callbacks, timers, threads, chat handlers,
HTTP endpoints, resource identities, lookups, mutations, return overrides, or raw
`ProcessEvent` access.

## Adding Creator-Facing Examples

New first-party Plugin Hub seed examples should be small, safe-disabled, and native to the
current Obelisk C ABI. The fastest useful additions after `v0.1` are descriptor readers,
passive copied-chat parsers, process-local timer utilities, and copied policy auditors.
The current tree already has examples for those categories. Treat new first-party work as
a promotion or refinement of the existing examples unless a separate copied-data surface
has passed the capability-matrix evidence gate.

Do not add a first-party example that implies commands, permissions, economy, homes, RCON,
inventory/item mutation, dino tools, tribe tools, transfer handling, structure placement
enforcement, identity, lookup, replies, send-chat, moderation, or ArkApi portability until
the matching public surface is promoted in the capability matrix and documented with its
own evidence gate.

Seed examples are production-ready only when they keep the safe default config above,
fail closed on missing capabilities or callbacks, validate instance scoping, unregister
owner-token handles on every shutdown or partial-init path, treat callback payloads as
callback-scope, keep mutable state process-local unless a locking model is documented,
and log only bounded, sanitized output.

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

When active, `oChatAudit` requires the public chat-event capability, timer capability, and
a non-zero owner token. It registers exactly one chat callback and one repeating timer,
then unregisters the timer before the chat callback during shutdown. Digest output is
process-local metadata only: accepted/malformed event counts, per-mode counts, total and
max byte sizes, bounded size buckets, and overflow count.

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
