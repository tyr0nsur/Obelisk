# Module Surface Roadmap

## Objective

Rank the next ARK/UE4 module surfaces from existing Obelisk evidence, prioritizing stable
v0.1 production value and copied-POD event feasibility.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Evidence only: committed docs, sanitized UFunction/ScriptStruct snapshots, target-set
  definitions, internal recognizer headers, and accepted copied-offline minimal, item,
  inventory-action, buff, dino, mission, and tribe compact layout artifacts.
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
- `structure-observer-intake`: fresh copied-offline regeneration accepted under
  `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z`;
  `6/6` accepted, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, and
  no blockers. This is layout-only structure backing for copied/redacted
  `GameplayPolicyEvent`; it does not promote public StructureEvents, identity, lookup,
  mutation, return override, raw params, or `ResourceHandle`.
- `buff-compact-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z`;
  `3/3` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, and no blockers for
  `PrimalBuff.AllowPostProcessEffect`, `PrimalBuff.BPBuffPreventUploading`, and
  `PrimalBuff.BP_OnBuffLifetimeUpdated`. This is internal layout evidence only,
  not public Buff SDK/runtime promotion.
- `buff-breadth-intake`: accepted offline layout evidence from
  `/servidor/ark/workspace-offline/buff-breadth-intake-second-source-20260530T091014Z`;
  `3/3` accepted, `gate_mode=second_source_promotion`,
  `promotion_gate.ready=true`, `promotion_gate.ready_scope=layout_only`, and
  `promotion_gate.promotion_ready=false` for
  `PrimalBuff.BuffOverrideInventoryAccessInput`, `PrimalBuff.BPCustomAllowAddBuff`, and
  `PrimalBuff.BPPreventAddingOtherBuff`. This broadens internal Buff layout evidence only;
  it does not promote public Buff SDK/runtime hooks, class/object exposure, mutation,
  return override, raw params, `ResourceHandle`, or gameplay semantics.
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
- `transfer-ufunction-intake`: accepted layout-only second-source evidence for 7/7
  comparable targets. This supersedes the older missing-second-source line but does not
  promote a public Transfer SDK, runtime hooks, payload decoding, identity, mutation,
  return override, or `ResourceHandle`.
- `transfer-scriptstruct`: accepted layout-only second-source evidence for 2/2
  comparable ScriptStruct targets. Payload decoding remains no-go because tribute structs
  contain names, byte arrays, ids, class refs, stats, and server names.
- `sdk.admin`: documentation-only; no committed admin snapshot target set.

## Result

Recommended lane order:

RC stays centered on `GameplayPolicyEvent`, the minimal copied `ChatMessageEvent`,
`DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`. The module ranking below is
post-RC/internal research direction unless a later focused gate explicitly changes release
scope.

Promotion gate for every module lane is: exact layout target set, fixture coverage,
second-source/static evidence, copied-data ownership and redaction policy, approved
runtime observation, internal dispatcher lifetime cleanup, then append-only public SDK ABI
and installed consumer tests. `promotion_gate.ready=true`, accepted targets, target-set
names, and labels such as `sdk.inventory` or `sdk.buffs` describe the layout/evidence rung
only; they do not turn target-set labels into public SDK names.

Roadmap-to-Plugin-Hub alignment for contributors:

- `hub foundation` is the only release-supported seed lane now, but only as archived
  post-SDK-complete planning while the complete SDK blocker chain remains open.
- Active rounds are SDK-complete-first: identity/principal evidence, permissions/admin
  query-only groundwork, command response, and then commands/replies. Plugin Hub
  foundation is parked until the SDK blocker chain is resolved.
- `gameplay policy backing` protects the existing copied/redacted `GameplayPolicyEvent`
  surface; it does not authorize new Inventory, Items, StructureEvents, enforcement,
  identity, lookup, mutation, return-override, or ArkApi compatibility claims.
- `internal recognizer planning` stays offline/test-only until a later note names the
  exact target, copied payload, privacy rule, lifecycle rule, evidence gate, runtime
  observation gate, and append-only ABI/consumer-test plan.

0. `resources / ResourceHandle`: do not run more broad FName/GObjects/UFunction scans for
   this track on the current binary. Existing offline evidence is strong enough for target
   work; the live blocker is lifecycle/flag semantics and a fail-closed handle contract.
   Treat `0x100` as a hard-invalid internal candidate and `0x4000` as mode-dependent
   weak-delegate evidence only until rejected runtime samples or stronger static semantics
   prove a safe public policy.
1. `structures lane`: keep `GameplayPolicyEvent` as the only promoted public gameplay
   surface; next work should harden docs/evidence around copied scalar fields, not add raw
   StructureEvents.
2. `inventory lane`: current best hardened backing inside existing `GameplayPolicyEvent`.
   `CanUse` and `AllowRemoteAddToInventory` are copied-bool only, require exact full field
   sequences, and reject forged metadata-only ranges.
3. `items lane`: best post-RC internal bridge candidate after inventory hardening, but only
   for return-only observations that already fit the public `GameplayPolicyEvent`
   `RETURN_VALUE` field mask. Do not weaken `InventoryPolicyEventDispatcher::CanUse` by
   fabricating `BIgnoreCooldown` from item-only fields.
4. `mission lane`: useful post-RC internal recognizer candidate after item return-only
   evidence is preserved. Keep it as a reduced copied-bool observer with
   object/player/controller/array fields recognition-only.
5. `items detail lane`: `ue/ItemReflection` now implements the first fixture-backed, SHA-gated
   internal recognizer for `PrimalItem.AllowEquipItem`, `CanRepair`, `CraftBlueprint`, and
   `UseItemOntoItem`. It exposes only bool ranges; `toInventory`, `DestinationItem`,
   `AdditionalData`, `ItemNetID`, identity, mutation, return override, hooks,
   dispatchers, and SDK callbacks stay blocked.
6. `dino lane`: compact passenger/carry policy shapes now have accepted second-source
   layout evidence and are useful internal recognizer inputs after inventory. They remain
   blocked from public payloads because raw actor identity, object lifetime, resource
   handles, taming, attack, mutation, and return-override semantics are unresolved.
7. `buff lane`: good reflection coverage for bool-return, bool-input, class-ref, and
   zero-param shapes after compact plus breadth second-source evidence; poorer product
   candidate until buff semantics, object/class redaction, and no-override policy are
   explicit.
8. `tribe lane`: accepted permission and membership layout evidence is valuable, but public
   usefulness is identity-sensitive and array/string targets remain blocked.
9. `transfer lane`: broad fixture coverage and layout-only second-source evidence exist,
   including tribute structs, but transfer payloads are sensitive and array/string/nested
   struct ownership is unresolved. The only clean post-RC first slice is
   `ServerTransferredPlayerConfirmationResult.bAccept` as an internal copied bool.
10. `admin/permissions lane`: keep documentation-only until a permission model and abuse
    controls exist.

## Next v1 Round Recommendation

Run the next v1 planning round as a narrow complete-SDK blocker pass, not a new Plugin Hub
or module promotion pass:

1. `player identity/principal`: finish approved runtime principal lifecycle evidence and
   keep it consume-only until promotion gates pass.
2. `permissions/admin`: prepare query-only fail-closed internal groundwork on top of
   promoted principal semantics; do not add public ABI yet.
3. `command response/commands`: keep blocked until identity and permissions are promoted.
4. `gameplay policy backing`: preserve the already-public copied/redacted
   `GameplayPolicyEvent` path by tightening inventory/structure/item return-only
   evidence and tests. Treat every accepted target set here as backing evidence for
   existing copied POD fields, not as a new Inventory, Structure, or Items SDK.
5. `internal recognizer planning`: keep mission as the first post-RC internal copied-bool
   planning thread after item return-only evidence is preserved. Buff, dino, tribe, and
   transfer remain lane-specific backlog until their blockers below are narrowed by named
   offline artifacts.

No-repeat rules for this round:

- Do not rerun broad FName, GObjects, UFunction, ReflectionScanner, core, or serial-sweep
  discovery on the current binary unless the hash changes or an existing artifact
  contradicts the accepted evidence.
- Do not use ArkApi/AseApi/NextGenPlugins as implementation sources; they remain names
  and demand signals only.
- Do not promote any `sdk.*` label, `promotion_gate.ready=true`, accepted target count, or
  compact layout artifact into a public SDK, runtime observer, identity/lookup contract,
  mutation path, return override, raw params, or `ResourceHandle`.
- Do not route work back to chat as the roadmap center. Chat remains a small copied
  notification example and regression surface.

## Copied-POD Candidates

- Structures already public through `GameplayPolicyEvent`: `ReturnValue`, `VariantIndex`,
  `BForceSet`, and `BForce`; pincode, player identity, character identity, object identity,
  raw params, UE pointers, and FName/GObjects indices stay redacted.
- Inventory future internal-only candidates: `bIgnoreCooldown`,
  `bRequestedByPlayer`, and `ReturnValue`; `invComp`, `ByPC`, `InventoryComp`, item ids,
  array contents, and struct payloads stay redacted.
- Items current internal-only recognizer fields: `AllowEquipItem.ReturnValue`,
  `CanRepair.bIgnoreInventoryRequirement`, `CanRepair.ReturnValue`,
  `CraftBlueprint.bConsumeResources`, and `UseItemOntoItem.ReturnValue`; `toInventory`,
  `DestinationItem`, `AdditionalData`, item/inventory identity, raw object refs, mutation,
  and return override stay blocked.
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
- Transfers future offline-only candidates: `ServerTransferredPlayerConfirmationResult`
  `bAccept` is the only clean first internal copied-scalar candidate. Spawn/region ints
  remain maybe/research-only; `PlayerDataID`, `IgnoreBedID`, dino classes, uploaded
  dino/object refs, tribute names, byte arrays, nested item data, and strings stay
  blocked.

## Promotion Blockers

- `ResourceHandle` is not blocked by lack of FName/UFunction discovery. It is blocked by
  `uobject_flags_validity_semantics_unproven`, lack of rejected object samples, and no
  accepted lifetime/revalidation contract across hook callbacks and possible object reuse.
- Hub foundation blockers: release docs/tests, installed packaging checks, descriptor and
  capability stability, fail-closed config behavior, and plugin lifecycle cleanup remain
  the only blockers on the next broadly v1-facing lane.
- Gameplay policy backing blockers: every added event kind still needs exact target-set
  membership, copied/redacted POD ownership, fixture and consume-gate coverage, no raw UE
  pointer exposure, no mutation, and no return override.
- Internal recognizer planning blockers: mission, buff, dino, tribe, and transfer work
  must each name the exact offline artifact and blocker it narrows; otherwise it is
  backlog, not a next-round task.
- Missing accepted second-source comparison roots for admin, broader non-compact
  target sets, and any broader module target set. Transfer UFunction and ScriptStruct
  layout-only second-source evidence is now accepted for its exact documented targets, but
  does not promote Transfer runtime work or public SDKs. The accepted minimal
  inventory/structure evidence is limited to four compact `UFunction` layouts, and the
  accepted buff/dino/mission/tribe compact evidence is limited to their exact compact
  target sets.
- Dinos still lack runtime observation, copied-data ownership, callback lifetime policy,
  SDK ABI design/tests, resource identity policy, and privacy/redaction policy; the
  accepted compact evidence only advances the offline layout rung.
- Structure fresh-evidence risk was resolved by regenerating `structure-observer-intake`
  from copied offline artifacts outside protected server paths; keep future promotion
  claims tied to the refreshed pack path above, not only to historical triage.
- Public SDK expansion requires append-only C ABI design, ABI layout tests, installed SDK
  consumer tests, owner-token lifecycle cleanup, capability docs, and explicit redaction
  statements per event.
- Runtime observation remains separate from fixture readiness and must use approved debug
  posture, exact metadata filters, non-zero budgets, no mutation, no return override, and
  no raw value logging.

## Next Steps

1. Keep v0.1 public scope centered on copied/redacted `GameplayPolicyEvent`.
2. Stop broad discovery loops on the current binary unless a hash/artifact contradiction
   appears; use existing GObjects/UFunction evidence for focused target-set work.
3. Make inventory the next internal observer candidate from the accepted minimal layout
   evidence, with copied-scalar payloads only.
4. Preserve item return-only evidence as the first post-RC bridge candidate after
   inventory hardening; do not map `bIgnoreInventoryRequirement` to `BIgnoreCooldown` or
   publish an Items SDK.
5. Do not route mission, tribe, buff, or dino toward public API or runtime promotion before
   RC; mission remains internal recognizer work after item return-only evidence.
6. Treat the accepted dino compact pair as internal layout evidence for later recognizer
   design only; do not build a public Dino SDK or runtime observer from it yet.
7. Keep buff compact and breadth target sets as accepted internal layout evidence only;
   any further buff work should be copied-payload/redaction design, not runtime hooks.
8. Keep tribe, transfer, and admin surfaces blocked from public ABI until identity,
   payload ownership, and permission policy are designed.
