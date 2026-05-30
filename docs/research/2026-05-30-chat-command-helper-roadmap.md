# Chat Command Helper Roadmap

## Objective

Define a plugin-author helper pattern for plugin-local text routing on top of the minimal
copied `ChatMessageEvent` payload without adding runtime ABI, identity, permission,
mutation, or chat-response semantics.

This is documentation-only design guidance. It is not a request to change
`include/obelisk/ObeliskApi.h`, `core/ChatEventDispatcher`, CMake targets, runtime
producer gates, or first-party plugin behavior.

## Decision

A helper is useful, but only as plugin-local source/example material after the RC line is
stable. It should not be promoted as a runtime service.

The helper should treat each matched command with:

- `principal=unknown`
- `send_mode` copied from `ChatMessageEvent`
- `sequence` copied only as a process-local diagnostic value
- copied command text owned by the plugin before the callback returns
- no sender, player, tribe, controller, connection, Steam/EOS, platform, actor, resource,
  map, or UE object identity

The helper may parse and route text inside the plugin process. It must not imply that
Obelisk can authorize the sender, send a reply, block chat, mutate chat, or resolve a
player.

## Non-Goals

- No new public runtime API, capability bit, public struct, enum, callback type, or C ABI.
- No command registration in `ObeliskApi`.
- No public command SDK claim for v0.1.
- No sender/player identity or per-player permission checks.
- No chat send, reply, moderation, block, mutation, or return override.
- No UE lookup, `UObject`, `UFunction`, `FString`, raw params, FName/GObjects index, or
  pointer-derived handle.
- No cross-process command state or shared registration handles.

## Helper Shape

Keep the first helper as source/example material owned by an individual plugin, not as a
runtime callback family. A plugin can implement the following private flow:

1. Subscribe to `ChatMessageEvent` using the existing owner-token handle API.
2. During the callback, validate `event`, `struct_size`, copied-payload flags, and message
   bounds.
3. Copy the UTF-8 message into plugin-owned memory before returning if any work may outlive
   the callback.
4. Match a plugin-owned prefix such as `!` or `/` from config.
5. Tokenize only the copied text.
6. Route to plugin-owned handlers using a static command table or config table.
7. Pass `principal=unknown` to every handler.
8. Log only sanitized command metadata, such as command name and rejection reason. Do not log
   raw chat text by default.

Any handler that needs a real player, permission, or response path must fail closed until a
future copied identity and response API exists.

## Config-Only Permissions

The only acceptable near-term permission model is global plugin config. Example shape:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "chat_command_helper": {
    "enabled": false,
    "prefixes": ["!"],
    "commands": {
      "help": {
        "enabled": true
      },
      "reload-local-cache": {
        "enabled": false
      }
    }
  }
}
```

Rules:

- `enabled=false` is the default.
- `allow_all_instances=false` and an empty `instance_allowlist` stay fail-closed.
- A command is either globally enabled for that plugin instance or disabled.
- There is no per-player, per-tribe, admin, group, role, ownership, or map permission.
- The helper must describe denials as global config denials, not authorization failures for a
  specific sender.

## Handler Contract

Private plugin handlers should receive a small copied context:

```text
principal=unknown
send_mode=<copied Obelisk chat send mode>
sequence=<process-local event sequence>
command=<parsed command name>
args=<plugin-owned copied tokens>
```

Handlers must assume the principal cannot be authenticated. Safe handler classes are limited
to plugin-local reads, diagnostics, metrics, or local state changes that are acceptable for
any chat sender on that instance. Risky operations stay disabled until a future API provides
copied identity, explicit permissions, and response/mutation semantics.

## ABI And Lifecycle Notes

- The helper depends only on the existing `ChatMessageEvent` subscription functions.
- It must perform the same `OBELISK_API_CAPABILITY_CHAT_EVENTS`, `struct_size`, owner token,
  and function-pointer checks documented in `docs/PLUGIN_ARCHITECTURE.md`.
- The plugin must unregister the chat callback during shutdown.
- The plugin must not store borrowed event pointers, message pointers, `ObeliskApi*`, or
  `ObeliskPluginInitContext` pointers beyond their documented lifetime.
- If command work is deferred to a worker, the copied command text and args are plugin-owned,
  and the plugin needs the normal worker shutdown/drain design before stability.

## Promotion Blockers

A real command module remains blocked on:

- copied sender/player identity with privacy and lifecycle rules;
- a permission service that fails closed and does not depend on pointer-derived IDs;
- a safe chat response path, if replies are part of the command model;
- clear behavior for cluster/shared-config deployments;
- ABI tests, SDK consumer tests, lifecycle tests, and public documentation;
- evidence that no command path implies chat moderation, mutation, return override, or UE
  lookup authority unless explicitly promoted.

## Recommended Placement

For now, keep this as a roadmap note plus a short cross-reference from plugin architecture
docs. Do not add a first-party `oCommand*` plugin or installed helper target until command
identity and permissions are designed, or until the project explicitly accepts an
experimental plugin-local example whose non-goals are enforced by guardrails.
