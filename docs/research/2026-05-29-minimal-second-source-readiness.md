# Minimal Second-Source Readiness

## Objective

Record the executed direct-root second-source intake result for the compact inventory and
structure UFunction target set.

## Artifact

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Offline workspace:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`
- Current validator refresh:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z`
- Readiness report:
  `pack/snapshot-comparison/readiness-report.json`
- Direct intake input binary/core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/`
- Current validator refresh input binary/core:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/`
- FName root slot: `0x5956f30`
- GObjects candidate used for snapshot regeneration: `0x595b7e0`

## Result

The executed intake used direct FName-root validation instead of a broad FName scan. The
root validation matched all requested clues:

```text
None=0
ClientMessage=4884
ServerChat=9619
SetActiveMissionDebugFlags=9622
```

Snapshot comparison result:

```text
gate_mode=second_source_promotion
promotion_gate.ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.layout_ready=true
promotion_gate.promotion_ready=false
promotion_gate.blockers=[]
targets=4
comparable=4
second_source_accepted=4
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
```

Accepted target modules:

```text
sdk_inventory: 2/2
  PrimalItem.AllowRemoteAddToInventory
  PrimalItem.CanUse

sdk_structures: 2/2
  PrimalStructure.AllowStructureAccess
  PrimalStructure.IsAllowedToDemolish
```

The refresh run also passed the current offline artifact consume gate:

```text
readiness-report.json: status=accepted
redacted-minimal/signatures.json: status=accepted
redacted signature artifact_status=candidate_only
redacted signature promotion_ready=false
redacted signature_count=4
```

Current artifact identities:

```text
/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/pack/snapshot-comparison/readiness-report.json
sha256=a51d48f537c19808b0612965236ca39cdfc69105dc8b6d524ac52cdc389e8255

/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/redacted-minimal/signatures.json
sha256=f02784d949da31d4ce1579cce8810d4c37509c5b4c202fe0e24b8a72a364791a

/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/redacted-minimal/consume-gate.json
sha256=e14747b2d8a27dac7e2116f30442b729abe685f521d2a91444e12f9be79b95e1
```

The persisted `redacted-minimal/signatures.json` is sufficient as a candidate-only bool
mask review artifact: it records `bool_masks.byte_mask=0x01` and
`bool_masks.field_mask=0xff` for `PrimalItem.CanUse.bIgnoreCooldown`,
`PrimalItem.CanUse.ReturnValue`,
`PrimalItem.AllowRemoteAddToInventory.bRequestedByPlayer`, and
`PrimalItem.AllowRemoteAddToInventory.ReturnValue`. It is not a strict target-set-coverage
artifact because it was generated from direct snapshots with `target_sets=[]` and no
`target_set_coverage` object. For a strict RC review pack, regenerate from the committed
snapshots with `scripts/build_redacted_ufunction_signatures.py --target-set
minimal-second-source-intake --json`; this reads sanitized fixtures only and does not
require a new core scan.

The strict RC review pack was regenerated from the committed snapshot manifest and
preserved outside Git:

```text
/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/signatures.json
sha256=034a03a926005ac78959e73528014c87b81e167d74aa6c9b8dfd36c92f31c9c9
signature_count=4
target_set_coverage=minimal-second-source-intake complete
targets=PrimalItem.CanUse, PrimalItem.AllowRemoteAddToInventory,
        PrimalStructure.AllowStructureAccess, PrimalStructure.IsAllowedToDemolish

/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/consume-gate.json
sha256=bf3c07a428beddc384bcaba7374214d10e235690d1ed198bcf5a2fe494d37719
status=accepted

/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/promote-gate.json
sha256=7695f9da7cafdef229c2eabd229fdc7ee881fa3ec60d50781b8e2fef8f1a36bc
status=blocked
blockers=promote_mode_signature_manifest_candidate_only,
         promote_mode_manifest_has_non_claims

/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/SHA256SUMS
sha256=c851625e6938082133f40c281ac551218c043193cd900c1c6bdf619472323184
```

Strict artifact non-claims:

```text
candidate-only redacted UFunction signature report
does not promote public SDK callbacks or public metadata helpers
does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides
```

This closes the target-set coverage traceability gap for RC review while preserving the
same candidate-only non-claims. Consume-mode acceptance is hygiene evidence only; promote
mode remains blocked by design.

## 2026-05-30 Consume Refresh

A focused offline refresh regenerated the same `minimal-second-source-intake` evidence
from committed fixtures plus the preserved second-source snapshot root:

```text
/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/
```

Result:

```text
target_sets=["minimal-second-source-intake"]
targets=4
comparable=4
second_source_accepted=4
second_source_missing=0
second_source_rejected=0
promotion_gate.ready=true
promotion_gate.layout_ready=true
promotion_gate.promotion_ready=false
readiness-report consume gate=status=accepted
redacted-minimal consume gate=status=accepted
```

Hashes:

```text
d6c96751fb486769c28a74d3e6f03cdc4ca9a1a67992721e845d202b2f3124d7  snapshot-comparison/readiness-report.json
83cee10c2837b39be3703a4dc52e46dcccdd3a971825db680939a2fc9d53806b  snapshot-comparison/offline-artifact-gate-consume.json
32264856a5ab8beeabe008ce9ad350d0705372304b0187624cb7818b43dfec9d  redacted-minimal/signatures.json
bbeacfab0bbc162cb5e596463a65cfbda33b8d7e6f9214a709a1d0776aeae9af  redacted-minimal/consume-gate.json
```

This refresh reinforces the copied `GameplayPolicyEvent` structure/inventory lane only.
It does not promote public Inventory SDK, public StructureEvents, object identity,
lookup, `ResourceHandle`, mutation, return override, runtime hook contracts, or raw UE
internals.

## Promotion Boundary

This promotes compact UFunction layout evidence for the listed inventory and structure
targets only. It does not promote:

- `GObjects` or `FUObjectArray` as a runtime-stable global;
- `ResourceHandle`, object identity, player identity, item identity, or inventory identity;
- raw `UObject*`, `UFunction*`, FName/GObjects indices, raw params, arrays, or structs;
- mutation, return override, or public Inventory SDK callbacks.

## Next Step

Use this evidence to harden copied-scalar observer work. For public API movement, keep the
existing bar: copied POD payloads, owner-token lifecycle cleanup, ABI layout tests,
installed SDK consumer tests, explicit redaction docs, and no UE internals crossing the
SDK boundary.
