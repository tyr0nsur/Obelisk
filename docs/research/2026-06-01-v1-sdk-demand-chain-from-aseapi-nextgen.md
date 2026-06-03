# v1 SDK Demand Chain From AseApi/NextGen

Date: 2026-06-01
Status: demand synthesis, not promotion evidence

## Purpose

Condense the ArkApi/AseApi/NextGenPlugins demand signal into one durable dependency
chain for Obelisk v1 planning:

```text
identity/principal -> permissions/admin -> command/response -> storage/mutation
```

The chain explains ordering only. It does not promote a public SDK surface, compatibility
target, runtime observer, command router, response API, persistence service, inventory
mutation, structure enforcement, or gameplay mutation path.

Primary inputs:

- [2026-05-30-aseapi-reference-scan.md](2026-05-30-aseapi-reference-scan.md)
- [2026-05-30-nextgenplugins-reference-inventory.md](2026-05-30-nextgenplugins-reference-inventory.md)
- [2026-05-31-v1-sdk-round-identity-static-demand-audit.md](2026-05-31-v1-sdk-round-identity-static-demand-audit.md)
- [2026-06-01-player-principal-policy-route.md](2026-06-01-player-principal-policy-route.md)
- [2026-06-01-permissions-query-failclosed-route.md](2026-06-01-permissions-query-failclosed-route.md)
- [2026-05-31-commands-principal-routing-contract.md](2026-05-31-commands-principal-routing-contract.md)
- [2026-05-31-operator-ingress-storage-blocker-brief.md](2026-05-31-operator-ingress-storage-blocker-brief.md)

## Dependency Chain

1. Identity/principal first.
   A future plugin-facing subject must be copied, opaque, generation-checked,
   privacy-scoped, and invalidated fail-closed. Permissions, commands, economy,
   homes, safe zones, rewards, moderation, and grants must consume this principal
   instead of rediscovering players through UE pointers, names, platform IDs, chat text,
   or object lookup.

2. Permissions/admin second.
   The only post-identity candidate is query-only, owner-scoped, capability-gated, and
   fail-closed over copied principals. `allow` decisions require runtime-owned authority
   provenance, policy generation, and policy epoch. Groups, grants, ban/kick, moderation
   actions, command routing, storage, and mutation remain separate surfaces.

3. Command/response third.
   Copied chat parsing can stay plugin-local with `principal=unknown`; it is not a
   command SDK. A real command/response surface needs promoted identity, promoted
   fail-closed permissions, owner-scoped command callback lifecycle, abuse controls,
   audit/redaction, and a copied response path. Static response-thunk orientation is
   navigation evidence only, not reply/send-chat readiness.

4. Storage/mutation last.
   Economy, kits, homes, teleport, safe zones, item grants, inventory changes, structure
   enforcement, RCON/operator workflows, and durable cooldowns need separate storage,
   ingress, audit, lifecycle, and mutation contracts. Identity and permissions do not
   automatically promote persistence, operator ingress, UE mutation, return override, or
   rollback semantics.

## Top Demand Families

- Permissions/admin: admin permissions, groups, checks, and operator permission flows.
  Blocked on copied principal plus query-only fail-closed authority provenance.
- Commands/responses: chat commands, aliases, help, no-permission replies, and
  broadcasts. Blocked on identity, permissions, response path, abuse policy, and audit
  policy.
- Economy/rewards: shop, kits, points, rewards, and balances. Blocked on identity,
  permissions, storage, commands/responses, and later safe grants.
- Homes/teleport/safe zones: player services, cooldowns, combat/enemy checks, and area
  rules. Blocked on identity, permissions, location/area policy, storage, mutation, and
  enforcement contracts.
- RCON/operator I/O: remote commands, reloads, Unicode text, and external ingress.
  Blocked on ingress trust model, secrets policy, audit, queue lifecycle, and storage.
- Inventory/items mutation: give-item/shop flows, item use/equip/repair policy, and
  inventory inspection. Blocked on copied policy evidence first, then identity, storage,
  safe mutation, and no public `ResourceHandle`.
- Structures/build policy: structure limits, ownership cleanup, no-collision, and
  build/access policy. Blocked on copied policy evidence first; no public structure
  identity or enforcement is promoted.
- Dinos/tribes/buffs-status/missions/transfers: carry/color/reward hooks, tribe features, transfer
  events, and mission events. Internal layout/redaction work only until identity,
  privacy, lifecycle, and copied payload gates exist.
- Lifecycle/ops foundation: descriptors, config/logging, timers, and crash/reload
  expectations. The current seed lane can improve foundation docs/tests without widening
  SDK claims.

## No-Claims

ArkApi, AseApi, and local NextGenPlugins material may inform names and demand grouping
only. Do not use it as architecture or ergonomics guidance, and do not copy or port:

- source code, control flow, command parsers, schemas, constants, return semantics, or
  plugin behavior;
- offsets, vtables, raw layouts, direct native-call wrappers, pointer accessors, or
  Windows/MSVC ABI assumptions;
- raw UE pointers, raw `ProcessEvent` params, `UObject`, `UFunction`, `FString`,
  FName/GObjects identity, `ResourceHandle`, object lookup, mutation, or return
  override patterns.

These materials are never authority for porting targets, API ergonomics, wrapper
semantics, command parser behavior, timer behavior, return semantics, return override
semantics, support-tier classification, offsets, layouts, ABI, schemas, constants, or
source code.

This note is also not evidence for ArkApi/AseApi compatibility, public v1 completion,
public identity, public permissions, command replies, send-chat, storage, operator
ingress, inventory/item SDKs, structure SDKs, economy SDKs, or gameplay mutation.

Use the chain to rank future Obelisk-native design work. Every promoted surface still
needs its own Linux evidence, copied POD C ABI design, privacy/ownership policy,
lifecycle cleanup, capability gates, and SDK consumer tests. Public boundaries remain in
[../SDK_V1_COMPATIBILITY.md](../SDK_V1_COMPATIBILITY.md) and
[../PLUGIN_HUB_CONTRIBUTOR_PATH.md](../PLUGIN_HUB_CONTRIBUTOR_PATH.md).

## Validation

This note was produced from existing docs only. It did not use Git, Discord, servers,
runtime probes, protected server paths, or local source-code mining beyond the previously
recorded research notes.
