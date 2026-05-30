# Current Agent Handoff

Updated: 2026-05-30

This is an active routing table only: durable evidence belongs in `docs/research/`, resume facts in
`COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`.
historical recovery context is not active routing for the current head; use
`git log --oneline -1` for the current head rather than by the old 0-pre/0a/0b slicing
sequence.

## Active Objective

- `v0.1.0-rc.1` is published and should be treated as the frozen core-first RC baseline:
  Linux runtime, ProcessEvent hook infrastructure, plugin lifecycle, central install
  layout, `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- RC publication passed a clean release gate on the intended ref and exact tag/ref
  verification; stale tags are recreated only after rerunning the gate and are not reused.
- Do not expand or retag the RC for routine post-RC development. Future work should move
  toward a broader `v1.0` production-stable Obelisk core: general UE4 reflection,
  copied-data module APIs, lifecycle-safe plugins, operator lifecycle tooling, and enough
  compatibility surface for familiar ARK plugin concepts on Linux.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, gameplay/module timer abstractions, economy/database
  integrations, and admin tooling as module areas above the core. Promote each only
  through copied-data ABI, privacy, lifecycle, and second-source/static evidence gates.

## Hard Overrides

- GitHub work may be delegated only for an evidenced, stable milestone. Keep commits
  minimized; no routine push/checkpoint unless selected for validated publication. No tag
  or release-ref push is authorized without explicit release-manager/lead authorization
  for the current turn. Stale local tags are recreated only after rerunning the gate on
  the intended ref and are not reused or pushed.
- Any server-backed debug or beta work requires an approved live-ops brief for that turn:
  target instance/map, feature gates, marker/env changes, restart/start/stop window,
  notice path when players are involved, evidence capture, and rollback. No server target
  has standing approval for starts, stops, restarts, marker edits, or runtime observation.
  Technical progress is only a reason to request a scoped run; it is not approval by
  itself.
- Do not restart servers, edit `/servidor/ark`, change markers, run ReflectionScanner,
  attach ptrace/gcore, enable broad ProcessEvent tracing, or publish runtime observations
  outside an approved exact run. For in-game function tests, use an operator-approved
  notice before activation; keep operator secret endpoints out of repo files, skills,
  prompts, and handoff notes.
- Community updates are lead-only for major public modder-facing milestones, migrations,
  or releases; beta-test activation notices are separate live-ops messages.
  Webhook URLs live only in ignored `local/discord-webhooks.env`: use
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` for public modder-facing milestones and
  `OBELISK_BETA_TEST_WEBHOOK_URL` for approved in-game test windows. Send professional
  Discord embeds only; never expose raw URLs, player text, secrets, routine validation
  logs, or speculative reversing notes. Use `community` only for stable modder-facing
  milestones, `beta-test` only for approved player action windows, and no Discord for
  internal rounds or agent status. Explicit current-turn approval is required for every
  Discord send; publication approval does not imply Discord approval. Prefer `scripts/send_discord_embed.py --dry-run` as the
  guarded workflow; run it before any approved send, then verify title, description,
  status/scope, and 2-5 fields are public-safe.

## Current Routing Facts

- `v0.1.0-rc.1` is frozen. RC public scope remains limited to `GameplayPolicyEvent`, the
  minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`. It is not a production-stable `v1.0` claim and must
  not be expanded retroactively. Post-RC internal modeling does not change the RC public
  API; accepted RC UFunction second-source root evidence remains the publication baseline.
- `ObeliskApi` v1 remains append-only. New public surfaces need copied-data ownership,
  explicit capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- Promoted copied events remain non-authoritative: no UE pointers, raw params, object
  identity, lookup, mutation, return override, pincode/player text publication, or broad
  module SDK claim.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  control, and observers unless an exact approved debug window enables the matching
  env+marker pair.
- Current post-RC core primitive: owner-token process-local timers. They are core runtime
  utilities only, not gameplay/module timer abstractions or shared scheduler state. They
  are ABI append-only, zero-failure handles, one-shot/repeating, explicit unregister, and
  cleaned on plugin init failure/unload. Timer ids are not shared config, cluster state,
  UE identity, or persistent handles. `oProcessTimer` is the first-party process-local timer
  example and has SDK consumer coverage for disabled config, active one-shot callback,
  missing capability, short API, zero owner token, registration failure, post-registration
  init-failure cleanup, idempotent shutdown, and shutdown unregister.
- Internal bridges only: `StructureEventDispatcher`, `InventoryPolicyEventDispatcher`,
  Item/Mission/Transfer recognizers, weak-helper artifacts, GObjects evidence, and route
  observers are planning/evidence inputs until a separate promotion gate changes scope.
- Structure copied-event dispatch has been hardened to match the Inventory copied-event
  safety pattern: dispatch budget requires a live subscriber, matched invocations build
  one self-contained copied payload before reservation, copy/move rebinding keeps scalar
  spans owned, scalar range sizes are validated, and reader exceptions fail closed. This
  remains internal copied-scalar infrastructure only; it does not promote public
  StructureEvents, identity, lookup, mutation, return override, or `ResourceHandle`.
  Follow-up contract hardening also rejects any structure event whose scalar fields/types
  do not exactly match the public descriptor for that event kind, and the hook hot-path
  predicate now requires structure subscribers before dispatch budget can activate
  structure observation.
- ResourceHandle/public GObjects remain blocked. The old flag-policy artifact is obsolete;
  the durable rich-provenance refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/`.
  It now includes `artifact-pack.manifest.json`
  (`sha256=1f678c05461131055e4b18fd68862de431a27bbf49609297030ac62bf6f5478d`)
  and `SHA256SUMS`
  (`sha256=cf76ee33a8ea640233af7eff4de78171254a5ee5fa11de714259b27f2731a87a`).
  Consume mode accepts it and promote mode stays blocked with candidate-only/non-claim
  blockers; see `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.

## Priority Next Steps

- Preserve RC scope while moving toward `v1.0`: reduce architecture debt, improve evidence
  tooling, and promote only copied module APIs with strict gates.
- ArkServerApi/AseApi dictionary review confirms the fastest stable plugin-facing route
  remains copied `GameplayPolicyEvent` structure/inventory, especially the existing
  `PrimalItem.CanUse` and `PrimalItem.AllowRemoteAddToInventory` backing. Use AseApi only
  for names and familiar concept grouping. Do not copy offsets, layouts, wrappers,
  Windows ABI assumptions, raw pointer APIs, or implementation logic.
- The latest `minimal-second-source-intake` consume refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/`:
  4/4 targets accepted, consume gates accepted, and `promotion_ready=false`. It supports
  the copied `GameplayPolicyEvent` structure/inventory lane only, not Inventory SDK,
  StructureEvents, identity, lookup, mutation, return override, or raw UE internals.
  The pack has been normalized with relative checksums and `artifact-pack.manifest.json`
  (`sha256=072ff1f71c59e59189fa53922376dfc61d00915cfcd57817b1e5eacbc8200f8c`);
  `SHA256SUMS`
  (`sha256=21d8b0c0f30799b43110ddd4eed2484cc8c8527df878139dde28bc7d12598cf0`)
  verifies the manifest, readiness report, gate results, and redacted signatures.
- Current post-RC focus: Item return-only policy, Mission copied-bool observer,
  then Transfer `bAccept`. This is no RC public SDK/API promotion. Item return-only and
  Mission copied-bool now have internal/test-only consume-mode policy slices, and Mission
  copied-bool observer hardening also includes recognizer-side canonical-bool rejection
  plus hook-side `params + offset` provenance checks. Keep Item and Mission free of
  `ResourceHandle`, identity, mutation, return override, public Inventory SDK, public
  Mission SDK, hook wiring, marker/env, or runtime logs unless a future separate promotion
  gate changes scope. Transfer `bAccept` is likewise an internal/test-only consume-mode
  policy slice; this handoff does not authorize Transfer runtime work. ResourceHandle
  semantic work still needs helper evidence, mutation-window rejection, and a fail-closed
  contract.
  Commands/chat routing waits on player context, permissions, and safe response semantics.
  ArkServerApi/AseApi remains a names and behavior dictionary only; it is not a porting
  target or copying source. Do not copy offsets, layouts, ABI assumptions, wrappers, raw
  UE pointer APIs, or algorithmic implementations.
- The durable Item return-only policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z/`.
  It is evidence-only: consume mode accepts it, promote mode blocks it, and it does not
  authorize public Items/Inventory SDK, runtime hook wiring, markers/env, mutation, return
  override, identity, lookup, or `ResourceHandle`.
  It now includes relative `SHA256SUMS`
  (`sha256=ccd33e42337fd5b1ae3c51333c73ec17aeadef29d3c203b6680bb3be49c7a046`)
  and `artifact-pack.manifest.json`
  (`sha256=89e9b4af96472314055614824a2b2fce4a0b4343832ae38a2495d77411a5671a`).
  A local public-shape dry run accepted consume mode and kept promote mode blocked; the
  nearest future shape is only post-original copied bool observation through
  `GameplayPolicyEvent`, not an Inventory SDK or return override.
  A target-specific second-source pack is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-second-source-20260530T084918Z/`;
  readiness accepts 3/3 copied return-bool targets at `layout_only` scope, consume gate
  accepts, and promote gate remains blocked by evidence-only/non-claim blockers.
  The internal item helper can build-and-reserve a copied return-only observation in one
  operation and clears output on invalid attempts or exhausted budget; this remains
  test-only/internal and does not authorize public callbacks or runtime wiring.
- The durable Mission copied-bool policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z/`.
  It includes exact bool-tail evidence for each copied bool: `bool_field_size=1`,
  `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`.
  Its `artifact-pack.manifest.json` SHA256 is
  `b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb`
  and relative `SHA256SUMS`
  (`sha256=9dc277b8e3dddeed66d140a12654e4d5f7e7dc13b8b9aca75d96446c53069545`);
  consume mode accepts it, and promote mode blocks it with evidence-only/non-claim
  blockers. It copies only the five frozen Mission bool fields and keeps object refs plus
  `OutItemIDs` recognition-only.
- The durable Transfer `bAccept` policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z/`.
  It now includes `artifact-pack.manifest.json`
  (`sha256=dc35acbf63c9f22ffa5281952f2b651e034288f56ab9dec093cbfcfd368d841d`)
  and relative `SHA256SUMS`
  (`sha256=715f7c2b048370a74dbacfadd13d06496cf7e56867bb571351c2653d4fd297f8`);
  consume mode accepts it, and promote mode blocks it with evidence-only/non-claim
  blockers. It copies only `ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept`
  and keeps transfer payloads, ids, object/class refs, mutation, return override, hook
  wiring, dispatcher wiring, and public Transfer SDK blocked.
- Buff breadth now has accepted offline second-source layout evidence at
  `/servidor/ark/workspace-offline/buff-breadth-intake-second-source-20260530T091014Z/`.
  The target set is exactly `PrimalBuff.BuffOverrideInventoryAccessInput`,
  `PrimalBuff.BPCustomAllowAddBuff`, and `PrimalBuff.BPPreventAddingOtherBuff`; readiness
  accepts 3/3 comparable targets at layout-only scope and consume gate accepts the report.
  This is not a public Buff SDK/runtime promotion and does not authorize hooks, callbacks,
  object/class exposure, mutation, return override, raw params, `ResourceHandle`, or
  gameplay semantics.
- Do not rerun broad FName, GObjects, or core scans for ResourceHandle unless the binary
  hash changes or evidence contradicts current roots/candidates. The next ResourceHandle
  work should use the durable flag-policy refresh as internal static input and focus on
  mutation-window rejection, runtime negative samples, and a fail-closed lookup contract.
  Keep the internal label `InternalUObjectRevalidationCandidate`; do not expose
  ResourceHandle, GObjects, identity, lookup, lifecycle names, mutation, return override,
  object indices, serials, or UE pointers to plugins.
  The offline flag-policy report/gate now requires an explicit internal revalidation
  contract: frame-local only, post-callback lookup rejected, `0x100` rejected, `0x4000`
  rejected by default, output limited to copied bool/reason or Obelisk-owned copied data,
  and public API not promoted. The consume gate also validates the exact
  `weak_helper_caller_mode` shape/flag rules, rejects candidate fields outside the known
  contract, and blocks extra blocker/non-claim text that overclaims public
  `ResourceHandle`, lookup, SDK, runtime, or callback readiness.
- Chat command ergonomics should start as a plugin-local parser/helper over the existing
  copied `ChatMessageEvent`, not as a new ABI. The minimum contract is callback-scope
  slices over copied UTF-8 bytes with valid ABI/version/struct-size/send-mode checks.
  Player identity, permissions, targeting, chat send/reply, moderation/blocking, mutation,
  and return override remain blocked.
- Any future live/player validation requires a new approved live-ops brief and, when
  players are involved, a beta-test notice through the configured local webhook variable.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, and stale-agent cleanup.
- Sub-agents receive scoped expert tasks, not leader cadence or unrelated project policy.
- Before each sub-agent round: close stale agents, assign expert role, declare
  read-only/edit paths, declare allowed paths and required skills, pass only the skills
  required for that scope, state validation expected, state the expected decision, and
  keep integration with lead.
