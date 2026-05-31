# v0.2 Module Priority

Date: 2026-05-31

## Objective

Compare the current module lanes in `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md` and
`docs/research/README.md`, then select the one module surface after copied chat and
copied gameplay policy that has the best evidence-to-value ratio for v0.2 planning.

This note is prioritization only. It does not promote a public SDK, callback family,
runtime observer, descriptor, mutation path, return override, object identity, player
identity, lookup API, or ArkApi/NextGenPlugins compatibility target.

## Inputs

- `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`
- `docs/research/README.md`
- `docs/research/2026-05-29-module-surface-roadmap.md`
- `docs/research/2026-05-30-post-rc-targetset-priorities.md`
- `docs/research/2026-05-30-mission-copied-bool-observer-plan.md`
- `docs/research/2026-05-29-dino-compact-second-source-readiness.md`
- `docs/research/2026-05-30-player-identity-lifecycle-plan.md`
- `docs/research/2026-05-31-structure-build-policy-focal-snapshot-planner.md`

ArkServerApi/AseApi and NextGenPlugins are treated only as names and demand dictionaries.
No offsets, layouts, wrappers, ABI choices, behavior, control flow, or source-derived
implementation guidance are used here.

## Matrix And README Alignment

The Plugin Hub matrix and research README agree on the current support boundary:

- Production Plugin Hub seeds are still foundation work only: lifecycle/config/logging,
  descriptor/catalog consumers, process-local timers, packaging, and fail-closed
  capability checks.
- Passive copied chat parsing and copied `GameplayPolicyEvent` auditing are experimental
  pattern examples or promoted copied-policy backing, not general Chat, Command,
  Inventory, Items, StructureEvents, moderation, enforcement, identity, mutation, or
  return-override SDKs.
- The next module lanes are internal or planning-only until each lane has an exact
  copied payload, redaction/privacy policy, lifecycle cleanup, second-source/static
  evidence, runtime-observation approval, ABI tests, and installed SDK consumer coverage.

The README is slightly more specific than the matrix about the post-chat/policy research
order: after hub foundation and gameplay-policy backing, it names Mission as the selected
internal copied-bool planning thread, with Dino, Buff, Structure build-policy, Player
identity, Tribe, Transfer, and Admin/permissions behind it.

## Product vs Technical Priority

The Mission copied-bool lane is the best **technical hardening** target because its copied
payload is small, fixture-backed, and easy to keep non-identifying. It is not the best
**Plugin Hub product** target. Without identity, mutation, rewards, transfers,
progression state, commands, or runtime observation, Mission exposes too little for
creator-facing modules beyond passive aggregate telemetry and QA/regression checks.

For future Plugin Hub value, Structure aggregate/census, Dino aggregate/census, or Buff
aggregate/census may become better product-facing directions if they can be kept
aggregate, privacy-preserving, and copied-data only. They are not ready today: each still
needs its own evidence, redaction policy, lifecycle tests, and promotion gate. This note
therefore prioritizes Mission only as an internal v0.2 hardening lane, not as a public
Plugin Hub module.

## Ranked Recommendation

1. **Mission copied-bool internal bridge**

   Best v0.2 technical hardening ratio after chat and gameplay policy. The lane has
   accepted `mission-compact-intake` layout evidence, a frozen four-function surface,
   exact one-byte bool-tail rules, a consume-accepted focused policy artifact,
   recognizer/helper test coverage, and a narrow copied payload: five canonical bool
   fields. Object, player/controller, mission, and item-array fields can stay
   recognition-only, which makes the slice smaller than identity-heavy player, tribe,
   transfer, dino, or structure build-policy work. The v0.2 deliverable should remain
   internal/test-only: preserve and harden the default-off Mission copied-bool observer
   contract, not publish a Mission SDK or production Plugin Hub mission module.

2. **Dino compact recognizer**

   Good follow-up because `dino-compact-intake` has accepted second-source layout evidence
   for `AddPassenger` and `AllowCarryCharacter`, plus clear scalar candidates. It ranks
   behind Mission because exact recognition still depends on object parameters and needs a
   fresh scalar-only redaction/lifecycle review before any copied bridge.

3. **Buff compact/breadth recognizer hardening**

   Useful offline evidence and recognizer coverage exist, but the product value is less
   direct and class/object semantics remain unclear. Keep this as fixture/redaction
   hardening, not runtime or public API work.

4. **Structure build-policy focal snapshot**

   High operator demand, but current evidence is still a planner and guardrail path. It
   lacks one exact sanitized candidate snapshot, distinct second-source layout acceptance,
   copied payload policy, and any promotion basis for build-policy SDK, denial, mutation,
   or return override.

5. **Player identity lifecycle**

   High strategic value because many future modules need identity, permissions, replies,
   moderation, ownership, and persistence. It is still guidance-only: no accepted
   login/logout target set, stable copied identity, privacy policy, lookup semantics, or
   public SDK exists.

6. **Tribe and Transfer**

   Both have useful layout evidence, but the first public value is identity-sensitive.
   Tribe carries player/tribe IDs, logs, arrays, strings, permissions, and privacy risk.
   Transfer carries uploaded/downloaded player, dino, item, nested struct, string, and
   byte-array risk. Keep both internal/layout-only.

7. **Admin, permissions, economy, storage, RCON, commands, homes, kits, shops, teleports,
   webhooks, and broader inventory/item mutation**

   These are demand signals only until identity, permission/abuse controls, persistence or
   operator ingress, mutation policy, lifecycle, and ABI gates exist.

## Selected v0.2 Surface

Choose **Mission copied-bool internal bridge** as the one module surface to prioritize
after copied chat and copied gameplay policy for internal hardening. Do not present this
as the leading product-facing Plugin Hub category.

The immediate v0.2 scope should be:

- keep the surface internal/test-only and default-off;
- preserve exactly the frozen Mission targets and five copied bool fields;
- keep `MissionType.GetPlayerUsableItems` recognition-only with copied bool count `0`;
- strengthen fail-closed tests for disabled gates, unsupported SHA, non-mission FName
  values, zero budget, malformed bool bytes, forged copied ranges, and stale output
  clearing;
- prepare a later runtime-observation review checklist without requesting or implying an
  approved server window.

This gives v0.2 a module-shaped slice with real evidence and low payload risk while
avoiding the identity, mutation, and public SDK traps that block the higher-demand lanes.
Its useful outputs are internal recognizer confidence, copied-data ABI practice,
candidate aggregate telemetry, and QA/regression evidence, not a creator-facing Mission
feature set.

## Blockers

- No runtime observation is approved for Mission.
- No dispatcher lifecycle or public callback ABI exists for Mission.
- No public Mission resource kind, event kind, descriptor, capability bit, or installed
  SDK consumer test exists.
- Player/controller/character object refs, mission identity, item arrays, object payloads,
  strings, raw params, FName/GObjects indices, and `ResourceHandle` remain redacted or
  recognition-only.
- Any future runtime work still needs exact live-ops approval, supported binary SHA,
  default-off env/profile/marker gates, positive bounded budget, copied-log destination,
  rollback, and stable-posture verification.

## Non-Claims

This recommendation does not claim:

- public v0.2 Mission SDK readiness;
- production Plugin Hub mission module readiness;
- ArkApi/AseApi or NextGenPlugins compatibility;
- runtime hook, observer, dispatcher, descriptor, or ABI promotion;
- player identity, mission identity, item identity, object identity, lookup, or
  `ResourceHandle`;
- mutation, blocking, enforcement, return override, chat replies, commands, permissions,
  economy, storage, RCON, or webhooks;
- permission to run servers, touch `/servidor/ark`, run ReflectionScanner, ptrace, `gcore`,
  broad ProcessEvent tracing, Discord updates, Git commits, tags, or pushes.

## Validation

This pass was read-only except for this research note. It compared the matrix and research
index plus the dated module-priority notes listed above. No server tools, protected server
paths, scanners, ptrace, `gcore`, runtime probes, commits, tags, pushes, or Discord
actions were used.
