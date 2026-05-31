# Permissions/Admin Minimum Post-Identity

## Objective

Define the smallest safe `permissions/admin` design that can be considered only after
`obelisk.player_identity.v1` is promoted.

This note is documentation-only. It does not add public headers, runtime C++, tests,
capability bits, command routing, replies, send-chat, persistence, operator ingress,
moderation, kick/ban, live-server work, or public SDK availability.

## Inputs Reviewed

- `docs/public_sdk_surfaces.json`
- `docs/SDK_V1_COMPATIBILITY.md`
- `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`
- `docs/PLUGIN_HUB_FOUNDATION_V1.md`
- `docs/research/2026-05-31-player-identity-first-evidence.md`
- `docs/research/2026-05-31-player-identity-targetset-gap.md`
- `docs/research/2026-05-31-player-identity-static-admin-thunks.md`
- `docs/research/2026-05-31-commands-principal-routing-contract.md`
- `docs/research/2026-05-30-chat-command-helper-roadmap.md`
- `docs/research/README.md`

## Current Decision

`obelisk.permissions_admin.v1` must remain `post-v1` and blocked today. The reviewed
surface docs already preserve the critical order:

```text
player_identity -> permissions_admin -> commands_replies
```

The improvement captured here is the minimum safe shape after identity, so later work has
a narrow target instead of widening permissions into command routers, admin actions, or
operator ingress.

## Minimum Scope After Identity

The first acceptable permission/admin surface should be query-only:

- Given a copied, already-authenticated principal from the promoted identity surface.
- Given a plugin-owned permission action name or action id.
- Given an optional plugin-owned resource scope string such as `global`, `chat`, or a
  future promoted module namespace.
- Return a copied decision: `deny`, `allow`, or `unknown`.
- Return copied diagnostic flags for fail-closed reasons that are safe to log, such as
  `missing_identity`, `unsupported_scope`, `policy_unavailable`, or `capability_disabled`.
- Treat `unknown` as denial for all command, mutation, economy, mobility, and moderation
  callers.

This is enough for later command/reply design to ask whether a principal may invoke a
plugin-owned command. It is not enough to send a reply, mutate the world, kick/ban a
player, reload policy, persist grants, or share state across instances.

## Explicit No-Scope

The minimum permission/admin surface must not include:

- public command router, command registration, replies, send-chat, broadcast, timed
  notices, moderation, blocking, kick, ban, whitelist, or RCON;
- group or role CRUD;
- grant/revoke APIs;
- database/storage schema, migrations, webhooks, sockets, secret handling, or operator
  ingress;
- player lookup, tribe lookup, object lookup, `ResourceHandle`, GObjects/FName indices,
  UE pointers, raw `ProcessEvent` params, raw `FString`, native-call wrappers, or ArkApi
  compatibility;
- inventory, item, economy, kit, reward, teleport, home, safe-zone, structure, dino,
  tribe, mission, transfer, or buff mutation authority;
- cross-instance persistence or cluster-wide authority unless a separate storage/ingress
  surface is promoted.

## ABI Shape

A future ABI should be append-only and capability-gated. Names below are placeholders for
design review, not approved public symbols:

```c
typedef struct ObeliskPermissionQuery {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t principal_handle;
    const char* action;
    size_t action_size;
    const char* scope;
    size_t scope_size;
    uint64_t request_flags;
} ObeliskPermissionQuery;

typedef struct ObeliskPermissionDecision {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t decision;
    uint32_t reason_flags;
} ObeliskPermissionDecision;

typedef int32_t (*ObeliskCheckPermissionFn)(
    uint64_t plugin_owner_token,
    const ObeliskPermissionQuery* query,
    ObeliskPermissionDecision* out_decision);
```

Required ABI properties:

- copied POD structs only;
- no STL, references, exceptions, classes, UE types, raw game memory, or borrowed output
  storage;
- `abi_version` and `struct_size` at the front of every cross-boundary struct;
- plugin checks the named capability bit, `ObeliskApi::struct_size`, non-null function
  pointer, and nonzero `plugin_owner_token` before calling;
- runtime validates `query->struct_size` and `out_decision->struct_size` before reading or
  writing appended fields;
- runtime clears or fully initializes `out_decision` on every path;
- missing capability, missing identity, malformed strings, unsupported scope, stale
  principal, unloaded policy, or invalid owner token returns failure or `deny/unknown`,
  never `allow`;
- no callback registration is required for the first query-only surface. If a future
  policy-change callback is added, it must use owner-token handle registration,
  owner-scoped unregister, and plugin-owner cleanup before `dlclose`.

## Owner And Capability Rules

Permission checks must be owner-scoped even when they are synchronous queries:

- The caller supplies the `plugin_owner_token` from `ObeliskPluginInitContext`.
- The runtime rejects owner token `0`, unknown owners, owner tokens from unloading
  plugins, and tokens not captured by the plugin's init-time `ObeliskApi` table.
- A plugin may only ask about actions in its own namespace unless a later reviewed
  cross-plugin authority model exists.
- Capabilities are captured at plugin init. Later marker/env changes must not widen an
  already-loaded plugin's permission authority.
- The permission surface must be separate from passive identity, command routing,
  response/send-chat, storage, and operator ingress capabilities.

## State Conventions

Default state is process-local and fail-closed:

- Permission decisions are computed against the current ARK server process only unless a
  promoted storage/ingress contract says otherwise.
- Policy state is not shared between maps, processes, or cluster nodes merely because the
  plugin binary or config directory is shared.
- Runtime handles, owner tokens, principal handles, callback handles, sequence values, and
  permission cache keys are process-local and must not be persisted.
- A plugin may maintain plugin-owned config policy, but Obelisk should not describe that
  as global, per-player, group, admin, or cluster authority.
- Principal invalidation from disconnect, transfer, restart, duplicate identity, malformed
  evidence, stale controller/state, or failed validation invalidates permission decisions.
- Cache entries must include principal generation or equivalent invalidation metadata from
  the promoted identity surface. Without that, caching must be disabled or callback-scope
  only.
- Logs should record sanitized action/scope names and safe reason flags only. Real player
  IDs, platform IDs, names, IPs, tribe IDs, and raw chat text stay redacted unless a
  separate privacy policy explicitly permits a copied form.

## Blockers

The minimum design cannot move beyond this note until all of these are resolved:

- `obelisk.player_identity.v1` is promoted with copied principal handles, privacy policy,
  lifecycle state, invalidation semantics, and multi-instance scope rules.
- The identity route closes the current `ServerListPlayers` and `ServerKickPlayer`
  snapshot gap and accepts lifecycle anchors, or records a different accepted identity
  evidence path.
- A public principal handle has clear scope: callback-local, process-local,
  restart-local, cluster-stable, or persistent.
- A permission policy source is chosen without implying unpromoted storage, secret
  ingress, database, RCON, webhooks, or operator reload behavior.
- Abuse controls exist for expensive checks, repeated denials, malformed strings,
  namespace probing, and command-driven callers.
- ABI tests, SDK consumer tests, and negative tests prove capability, owner-token,
  `struct_size`, stale-principal, unsupported-scope, and disabled-policy failures are
  fail-closed.
- Public docs explicitly keep commands/replies, send-chat, moderation, mutation,
  economy, mobility, storage, and operator ingress outside this first permission surface.

## Non-Claims

This note does not promote `obelisk.permissions_admin.v1`. It does not make permissions a
Foundation V1 or Plugin Hub release-supported seed. It does not authorize runtime work, server
access, new target sets, public ABI symbols, headers, tests, Discord updates, Git actions,
or command/reply APIs.
