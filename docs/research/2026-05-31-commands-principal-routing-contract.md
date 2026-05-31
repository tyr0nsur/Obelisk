# Commands And Principal Routing Contract

This note records the future contract shape for commands/principal routing without
promoting it into the public SDK. It is planning evidence only: no command router, reply
API, send-chat API, player lookup, permission system, moderation API, or raw UE surface is
available today.

## Boundary

The only current input that a plugin may rely on is copied `ChatMessageEvent` data:
`message`, `send_mode`, `flags`, and process-local `sequence`. Any plugin-local command
parsing over those bytes has `principal=unknown` and must remain plugin-owned.

Future command/principal routing must be a new copied C ABI surface, not a parser-only
extension to `ChatMessageEvent`. It needs a named capability bit captured from the
plugin's init-time `ObeliskApi` table, nonzero `plugin_owner_token`, owner-token handle
registration, owner-scoped unregister, plugin-owner cleanup before `dlclose`, and
callback-scope copied payloads.

## Required Future Inputs

- Promoted principal/player identity with opaque copied IDs, lifecycle state, privacy
  class, invalidation semantics, and cross-instance scope rules.
- Promoted permission/authority model that fails closed and is not derived from raw UE
  pointer identity, FName index, or transient object address.
- Command lifecycle boundaries: registration ownership, unregister behavior, in-flight
  callback rules, reload/unload cleanup, abuse/rate-limit policy, and audit/log redaction.
- Safe response path if replies or send-chat are included. Replies are not implied by
  command parsing.
- Multi-instance/cluster behavior for config, permissions, cooldowns, and any state that
  plugin authors might assume is shared.

## Blockers

- `obelisk.player_identity.v1` is still planning-only and lacks accepted lifecycle
  anchors, privacy/invalidation semantics, and full second-source evidence.
- `obelisk.permissions_admin.v1` is post-v1 and lacks an authority model, admin boundary,
  and abuse controls.
- No promoted copied response/send-chat API exists, so commands cannot promise replies.
- No owner-scoped command callback lifecycle exists in the public ABI.
- No public persistence or cross-instance consistency contract exists for command state,
  cooldowns, permissions, or economy-style actions.
- Raw `ProcessEvent`, raw FString, UE object pointers, FName/GObjects indices, ArkApi
  offsets/layouts, and direct native-call wrappers remain excluded from the public ABI.

## Next Admissible Preparation

Near-term work may only strengthen contract documentation, guardrail tests, or
test-only validation of the dependency order:

```text
identity -> permissions/admin -> command/chat response path -> commands/replies
```

This preparation must not add parser APIs, command registration, replies, send-chat,
public `CallProcessEvent`, moderation, player lookup, raw UE pointers, raw params, or
runtime delivery behavior. Identity must first provide copied principal semantics;
permissions/admin must then provide fail-closed authority provenance; only after both are
promoted may a copied response path define delivery semantics.

## Non-Claims

This note does not authorize runtime hooks, live-server tests, public SDK headers, command
registration APIs, moderation APIs, player lookup, message mutation, return override, or
send-chat/reply behavior. It only preserves the promotion criteria so later work does not
accidentally turn plugin-local chat parsing into an unsafe public command SDK.
