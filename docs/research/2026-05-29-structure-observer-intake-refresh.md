# Structure Observer Intake Refresh

## Objective

Regenerate fresh copied-offline second-source evidence for `structure-observer-intake`
after the current comparator showed historical structure triage was not enough for an RC
promotion claim.

## Inputs

- Source artifact: copied offline `arkserver2` / TheIsland core.
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- FName root slot: `0x5956f30`.
- GObjects candidate: `0x595b7e0`.
- Target set: `structure-observer-intake`.
- Output pack:
  `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z`.
- Comparison report:
  `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/pack/snapshot-comparison/readiness-report.json`.
- Committed base snapshot artifact identity:
  `artifact_kind=offline_core`,
  `artifact_sha256=1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e`,
  `capture_id=primary_core_20260527T031311Z`,
  `evidence_pack_id=primary_core_pack_20260527T031311Z`.
- Refreshed second-source snapshot artifact identity:
  `artifact_kind=offline_core`,
  `artifact_sha256=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`,
  `capture_id=core`,
  `evidence_pack_id=gobjects-sampling`.

No live server was started, restarted, attached, or modified. The run used only copied
offline artifacts under `/servidor/ark/workspace-offline`.

## Result

The refreshed comparison report accepted all six targets:

```text
gate_mode=second_source_promotion
evidence_scope=second_source_layout_evidence_only
promotion_gate.ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.layout_ready=true
promotion_gate.promotion_ready=false
promotion_gate.blockers=[]
totals.targets=6
totals.second_source_accepted=6
totals.second_source_missing=0
totals.second_source_rejected=0
```

Accepted targets:

- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`
- `PrimalStructure.SetVariant`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureSeating.CanSeat`

## Non-Claims

This is layout-only evidence for copied/redacted `GameplayPolicyEvent` structure backing.
It does not promote public `StructureEvents`, object identity, player identity, structure
identity, raw params, UE pointers, FName/GObjects runtime contracts, mutation, return
override, `pinCode`, or `ResourceHandle`.

`promotion_gate.ready=true` is the comparator's named-target-set layout gate. The
`promotion_gate.promotion_ready=false` value is intentional: the accepted comparison does
not by itself promote a public module SDK, runtime hook contract, object lookup, identity,
raw parameter access, mutation, return override, or handle surface.

## Commands

```bash
OUT=/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z

python3 scripts/run_second_source_core_intake.py \
  --binary /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --pack-dir "$OUT/pack" \
  --snapshot-root "$OUT/ufunction-snapshots" \
  --verified-fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --target-set structure-observer-intake \
  --base-root tests/fixtures/ufunction_snapshots \
  --execute
```
