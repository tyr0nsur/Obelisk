# HEAD RC Second-Source Refresh Gap

Date: 2026-05-30

## Summary

The historical `v0.1.0-rc.1` second-source UFunction root is valid only for that published
RC baseline. It must not be reused as final evidence for `v0.1.0-rc.2` or a later
candidate because current comparison gates require preserved BoolProperty tail metadata.

This was a release-evidence gap, not a runtime blocker. The gap was closed for
`v0.1.0-rc.2` by regenerating the second-source root from the existing independent
offline core with current tooling.

This note records the pre-item-return three-target-set RC refresh. For current
post-item-return checks, assemble all four public RC target sets:
`minimal-second-source-intake`, `structure-observer-intake`,
`item-return-only-policy-slice`, and `chat-message-intake`. The current helper requires
`--item-return-root` and produces 12 snapshots.

## Checked Roots

- Historical combined root: `/tmp/obelisk-rc-ufunction-second-source-root`
- Combined diagnostic root assembled in `/tmp`:
  `/tmp/obelisk-rc-ufunction-second-source-root-20260530T000000Z`
- Source roots used for the diagnostic root:
  - `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/ufunction-snapshots`
  - `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/ufunction-snapshots`
  - `/servidor/ark/workspace-offline/chat-message-intake-20260529T000000Z/ufunction-snapshots`

## Result

Command:

```bash
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root /tmp/obelisk-rc-ufunction-second-source-root-20260530T000000Z
```

Result:

```text
exit=2
readiness targets=9 comparable=9 blocked=0
promotion_gate ready=false blockers=inconclusive_second_source:8
sdk_chat accepted:1
sdk_inventory inconclusive:2
sdk_structures inconclusive:6
```

The only accepted RC target in that diagnostic root is
`ShooterPlayerController.ServerSendChatMessage`. The following eight targets are
inconclusive because the second-source snapshots predate the preserved bool-tail fields:

- `PrimalItem.AllowRemoteAddToInventory`
- `PrimalItem.CanUse`
- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`
- `PrimalStructure.SetVariant`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureSeating.CanSeat`

## Resolution Artifact

A refreshed second-source UFunction snapshot root was created for the eight targets above
with the current snapshot schema, including these fields on every accepted BoolProperty:

- `bool_field_size`
- `bool_byte_offset`
- `native_bool`
- `byte_mask`
- `field_mask`
- matching `bool_property_semantics.bool_field_size`
- matching `bool_property_semantics.bool_byte_offset`

The refreshed diagnostic root
`/tmp/obelisk-head-rc-second-source-root-20260530Trefresh` was generated from the existing
second-source offline core with `scripts/inspect_core_ufunctions.py --snapshot-json` and
accepted all nine pre-item-return RC targets:

```text
readiness targets=9 comparable=9 blocked=0 second_source_status=compared gate_mode=second_source_promotion
promotion_gate ready=true blockers=none
ufunction:sdk_chat targets=1 comparable=1 blocked=0 second_source=accepted:1,rejected:0,inconclusive:0,missing:0
ufunction:sdk_inventory targets=2 comparable=2 blocked=0 second_source=accepted:2,rejected:0,inconclusive:0,missing:0
ufunction:sdk_structures targets=6 comparable=6 blocked=0 second_source=accepted:6,rejected:0,inconclusive:0,missing:0
```

The published `v0.1.0-rc.2` tag used the same regeneration path for commit `1a7cd98`:

The final published `v0.1.0-rc.2` gate added `item-return-only-policy-slice`, so the
release-scope total is 12 snapshots across the four public RC target sets.
Any `promotion_gate ready=true` output in this note is RC UFunction layout-gate output
for the recorded ref and target sets only. It is not current approved runtime evidence,
public SDK promotion, or stable production readiness.

```text
root=/tmp/obelisk-head-rc-ufunction-second-source-root-1a7cd98
release-report-dir=/tmp/obelisk-rc-second-source-1a7cd98
tag=v0.1.0-rc.2
ref=1a7cd9816c8002846a40274d873a3ecc6ad742c0
```

Both concrete `/tmp` roots above are reproduction records only. They are not durable
workspace artifacts and must not be reused as final evidence for a later release ref.

Source identity used for the refreshed inventory/structure snapshots:

- Core path: `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- `artifact_sha256=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- `capture_id=core`
- `evidence_pack_id=gobjects-sampling`
- `gobjects=0x595b7e0`
- `fname_root_slot=0x5956f30`

Example generation command:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --outer-exact PrimalItem \
  --name-exact CanUse \
  --inspection-mode ufunction \
  --snapshot-json \
  --evidence-ark-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --evidence-artifact-sha256 62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78 \
  --evidence-capture-id core \
  --evidence-pack-id gobjects-sampling \
  --evidence-obelisk-commit <commit> \
  --evidence-source offline_core \
  --evidence-status candidate-only
```

For future release candidates, a newly regenerated second-source root for the intended
release ref, not either concrete `/tmp` root recorded above, must pass:

```bash
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root <refreshed-second-source-ufunction-root>
```

Then rerun the full release gate on a clean intended ref:

```bash
rm -rf /tmp/obelisk-rc-second-source
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root <refreshed-second-source-ufunction-root> \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set structure-observer-intake \
  --ufunction-second-source-target-set item-return-only-policy-slice \
  --ufunction-second-source-target-set chat-message-intake \
  --second-source-report-dir /tmp/obelisk-rc-second-source
```

## Non-Claims

- This does not invalidate the already published `v0.1.0-rc.1` evidence.
- This records the `v0.1.0-rc.2` publication evidence state; it is not standing evidence
  for later release refs.
- This does not promote Inventory, Items, Structures, ResourceHandle, lookup, mutation,
  return override, raw params, or public module SDKs.
- Do not satisfy this gap by copying bool-tail fields from committed fixtures into old
  second-source snapshots. The refreshed root must come from a distinct second-source
  artifact generated with current tooling.
