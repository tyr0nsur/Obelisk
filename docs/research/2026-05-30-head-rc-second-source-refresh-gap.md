# HEAD RC Second-Source Refresh Gap

Date: 2026-05-30

## Summary

The historical `v0.1.0-rc.1` second-source UFunction root is valid only for the
published RC baseline. It must not be reused as final evidence for current `HEAD` or a
later candidate because current comparison gates require preserved BoolProperty tail
metadata.

This is a release-evidence gap, not a runtime blocker. The chat target still compares, but
the inventory and structure RC targets need refreshed second-source snapshots generated
with the current tooling.

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

## Required Artifact

Create a refreshed second-source UFunction snapshot root for the eight targets above with
the current snapshot schema, including these fields on every accepted BoolProperty:

- `bool_field_size`
- `bool_byte_offset`
- `native_bool`
- `byte_mask`
- `field_mask`
- matching `bool_property_semantics.bool_field_size`
- matching `bool_property_semantics.bool_byte_offset`

The root must then pass:

```bash
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root <refreshed-second-source-ufunction-root>
```

After that, rerun the full release gate on a clean intended ref:

```bash
rm -rf /tmp/obelisk-rc-second-source
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root <refreshed-second-source-ufunction-root> \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set structure-observer-intake \
  --ufunction-second-source-target-set chat-message-intake \
  --second-source-report-dir /tmp/obelisk-rc-second-source
```

## Non-Claims

- This does not invalidate the already published `v0.1.0-rc.1` evidence.
- This does not promote Inventory, Items, Structures, ResourceHandle, lookup, mutation,
  return override, raw params, or public module SDKs.
- Do not satisfy this gap by copying bool-tail fields from committed fixtures into old
  second-source snapshots. The refreshed root must come from a distinct second-source
  artifact generated with current tooling.
