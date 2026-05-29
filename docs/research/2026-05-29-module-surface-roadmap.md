# Module Surface Roadmap

## Objective

Rank the next non-chat ARK/UE4 module surfaces from existing Obelisk evidence, prioritizing
stable v0.1 production value and copied-POD event feasibility.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Evidence only: committed docs, sanitized UFunction/ScriptStruct snapshots, target-set
  definitions, internal recognizer headers, and accepted copied-offline minimal, buff,
  dino, mission, and tribe compact layout artifacts.
- Live-server impact: none. No live-server reads, restarts, marker changes, runtime probes,
  ptrace, `gcore`, scanner runs, commits, public ABI edits, or pushes.

## Evidence

Current base readiness from committed fixtures plus accepted copied-offline layout
evidence:

- `minimal-second-source-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`;
  `4/4` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers for `PrimalItem.CanUse`,
  `PrimalItem.AllowRemoteAddToInventory`, `PrimalStructure.AllowStructureAccess`, and
  `PrimalStructure.IsAllowedToDemolish`.
- `structure-observer-intake`: 6/6 comparable; historical clean triage accepted, but
  promotion tooling still needs regenerated copied-offline artifacts for fresh review.
- `buff-compact-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z`;
  `3/3` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers for
  `PrimalBuff.AllowPostProcessEffect`, `PrimalBuff.BPBuffPreventUploading`, and
  `PrimalBuff.BP_OnBuffLifetimeUpdated`. This is internal layout evidence only,
  not public Buff SDK/runtime promotion.
- `dino-compact-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z`;
  `2/2` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers for
  `PrimalDinoCharacter.AddPassenger` and `PrimalDinoCharacter.AllowCarryCharacter`.
  This is internal layout evidence only, not a public Dino SDK/runtime promotion.
- `mission-compact-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z`;
  `4/4` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers. This is post-RC layout evidence only,
  not public Mission SDK/runtime promotion.
- `tribe-compact-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z`;
  `5/5` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers. This is post-RC layout evidence only;
  split scalar targets before considering public work.
- `transfer-ufunction-intake`: 7/7 comparable; second source missing.
- `transfer-scriptstruct`: 2/2 comparable; second source missing.
- `sdk.admin`: documentation-only; no committed admin snapshot target set.

## Result

Recommended order:

RC stays centered on `GameplayPolicyEvent` and `DescribeResourceKind`. The module ranking
below is post-RC/internal research direction unless a later focused gate explicitly changes
release scope.

1. `sdk.structures`: keep `GameplayPolicyEvent` as the only promoted public gameplay
   surface; next work should harden docs/evidence around copied scalar fields, not add raw
   StructureEvents.
2. `sdk.inventory`: next best candidate for a future internal copied-POD observer because
   `CanUse` and `AllowRemoteAddToInventory` have compact bool/object layouts and existing
   marker-gated observer policy.
3. `sdk.missions`: accepted compact lifecycle evidence makes it the cleaner first
   post-RC module candidate, but public work still needs copied-POD/redaction policy and
   array-presence-only handling.
4. `sdk.dinos`: compact passenger/carry policy shapes now have accepted second-source
   layout evidence and are useful internal recognizer inputs after inventory. They remain
   blocked from public payloads because raw actor identity, object lifetime, resource
   handles, taming, attack, mutation, and return-override semantics are unresolved.
5. `sdk.buffs`: good reflection coverage for bool-return and zero-param shapes; poorer
   product candidate until buff semantics, object/class redaction, and no-override policy
   are explicit.
6. `sdk.tribes`: accepted permission and membership layout evidence is valuable, but public
   usefulness is identity-sensitive and array/string targets remain blocked.
7. `sdk.transfers`: broad fixture coverage exists, including tribute structs, but transfer
   payloads are sensitive and array/string/nested struct ownership is unresolved.
8. `sdk.admin`: keep documentation-only until a permission model and abuse controls exist.

## Copied-POD Candidates

- Structures already public through `GameplayPolicyEvent`: `ReturnValue`, `VariantIndex`,
  `BForceSet`, and `BForce`; pincode, player identity, character identity, object identity,
  raw params, UE pointers, and FName/GObjects indices stay redacted.
- Inventory future internal-only candidates: `bIgnoreCooldown`,
  `bRequestedByPlayer`, and `ReturnValue`; `invComp`, `ByPC`, `InventoryComp`, item ids,
  array contents, and struct payloads stay redacted.
- Dinos accepted internal layout-only candidates: `PassengerSeatIndex`,
  `bForcePassenger`, `bAllowFlyersAndWaterDinos`, `bSkipLineTrace`, and `ReturnValue`
  from `AddPassenger`/`AllowCarryCharacter`; character/dino object identity, raw
  `UObject*`, `InternalIndex`, FName/GObjects indices, resource handles, mutation, return
  overrides, and public callbacks stay blocked.
- Buffs future internal-only candidates: `bInputPressed` and `ReturnValue`; controller,
  character, damage-causer, and class pointers stay redacted.
- Missions post-RC internal candidates: copied bool lifecycle state and array
  presence/count only after policy exists; player/controller/mission identity, item array
  contents, object pointers, mutation, and return overrides stay redacted.
- Tribes future internal-only candidates: `TribeGroupPermission` and `ReturnValue`; player
  ids, tribe/object identity, logs, mission tags, and online arrays stay redacted.
- Transfers future offline-only candidates: scalar spawn/region ids, confirmation bool,
  `PlayerDataID`, and `IgnoreBedID` only as redacted/internal fields; dino classes,
  uploaded dino/object refs, tribute names, byte arrays, nested item data, and strings stay
  blocked.

## Promotion Blockers

- Missing accepted second-source comparison roots for transfer, admin, broader non-compact
  target sets, and any broader module target set. The accepted minimal
  inventory/structure evidence is limited to four compact `UFunction` layouts, and the
  accepted buff/dino/mission/tribe compact evidence is limited to their exact compact
  target sets.
- Dinos still lack runtime observation, copied-data ownership, callback lifetime policy,
  SDK ABI design/tests, resource identity policy, and privacy/redaction policy; the
  accepted compact evidence only advances the offline layout rung.
- Historical structure/intake triage must be regenerated from copied offline artifacts
  outside protected server paths before being reused as fresh promotion evidence.
- Public SDK expansion requires append-only C ABI design, ABI layout tests, installed SDK
  consumer tests, owner-token lifecycle cleanup, capability docs, and explicit redaction
  statements per event.
- Runtime observation remains separate from fixture readiness and must use approved debug
  posture, exact metadata filters, non-zero budgets, no mutation, no return override, and
  no raw value logging.

## Next Steps

1. Keep v0.1 public scope centered on copied/redacted `GameplayPolicyEvent`.
2. Make inventory the next internal observer candidate from the accepted minimal layout
   evidence, with copied-scalar payloads only.
3. Do not route mission, tribe, buff, or dino toward public API or runtime promotion before
   RC; mission is only the first post-RC module candidate after an explicit gate.
4. Treat the accepted dino compact pair as internal layout evidence for later recognizer
   design only; do not build a public Dino SDK or runtime observer from it yet.
5. Keep buff compact as accepted internal layout evidence only; any further buff work
   should be fixture/offline expansion or copied-payload design, not runtime hooks.
6. Keep tribe, transfer, and admin surfaces blocked from public ABI until identity,
   payload ownership, and permission policy are designed.
