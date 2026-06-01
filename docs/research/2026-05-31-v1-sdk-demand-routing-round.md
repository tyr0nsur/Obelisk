# v1 SDK Demand Routing Round

Date: 2026-05-31

Scope: read-only demand and route audit for moving Obelisk from the core-first RC toward
a complete v1 SDK. Local ArkApi/AseApi and NextGenPlugins material is treated only as a
names/demand/architecture reference; no source, offsets, layouts, ABI assumptions, command parsers,
schemas, constants, or implementations are copied.

## Demand Map

Observed plugin-author demand clusters map to existing v1 blockers rather than new broad
surfaces:

- permissions/admin checks -> `obelisk.permissions_admin.v1`
- commands, replies, chat routing, notices -> `obelisk.commands_replies.v1`
- RCON/operator ingress, Unicode/operator text, storage/webhooks ->
  `obelisk.operator_ingress_storage.v1`
- economy, shops, kits, rewards, homes, teleport, safe zones ->
  `obelisk.player_services_economy_mobility.v1` plus later item/inventory work
- structure limits, ownership/census, placement/collision policy ->
  `obelisk.structure_census.v1`

## Route Decision

`obelisk.player_identity.v1` remains the first critical dependency. It unlocks the
authority model for permissions/admin, commands/replies, structure ownership/census,
economy, mobility, and inventory/item mutation. The current blocker is not another broad
static scan: it is the missing non-protected `obelisk.core-dump-evidence-pack.v1` followed
by a complete `obelisk.reflection-inventory-pack.v1` for
`players-identity-lifecycle-intake`.

Structure aggregate/census is the safest near-term module hardening lane because it can
remain internal, copied-scalar only, read-only, default-off, consume-only, and
promote-blocked. It must not become build-policy enforcement, `StructureEvents`, object
lookup, ownership lookup, exact coordinates, identity, mutation, return override, or a
public SDK claim.

Inventory/items mutation remains a later lane because it needs identity, item/inventory
lookup, authority, rollback, privacy, abuse controls, and mutation semantics. It does not
fit the current copied-data/no-identity/no-mutation/no-return-override slice.

## Guardrail Outcomes

- Public v1 manifest lists now need exact agreement between
  `post_v1_or_excluded_surfaces` and surface statuses of `post-v1` or `excluded`.
- Static player-identity orientation is now suitable for a shared candidate-only contract
  check, but still not an offline artifact gate or promotion source.
- Plugin-owner cleanup guardrails now explicitly require public v1 registration maps to
  be cleaned before underlying dispatcher cleanup.

## Non-Claims

This note does not promote public identity, permissions, commands, operator ingress,
storage, economy, mobility, structure census, inventory/items mutation, lookup,
`ResourceHandle`, mutation, return override, runtime hooks, or v1 completion.
