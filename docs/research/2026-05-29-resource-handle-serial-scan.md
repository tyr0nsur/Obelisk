# ResourceHandle Serial Scan

## Objective

Check whether copied offline cores contain `FUObjectItem+0x8` nonzero serial candidates and
`UObject+0x8` flag samples with masks `0x100` or `0x4000`. This targets the current
`ResourceHandle` blocker without touching a live server.

This note does not promote public object identity, lookup, mutation, return overrides, or
post-callback handles.

## Inputs

- Repo: `/home/flowcommunity-ark/Obelisk`
- Binary hash: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- `GUObjectArray` candidate: `0x595b7e0`
- `FName` root slot: `0x5956f30`
- Cores scanned:
  - `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
  - `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- Output directory:
  `/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529`

## Command

```bash
python3 scripts/scan_resource_handle_serials.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --max-objects 200000 \
  --label vanilla \
  --output /servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/vanilla-serial-scan.redacted.json

python3 scripts/scan_resource_handle_serials.py \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --max-objects 200000 \
  --label second_source \
  --output /servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/second_source-serial-scan.redacted.json
```

## Result

Both cores produced the same high-level counts for the first 200,000 object slots:

```text
objects_read=198147
serial_nonzero=817
serial_zero=197330
serial_missing=0
internal_index_mismatch=0
flags_0x100=0
flags_0x4000=0
```

The first repeated nonzero serial samples start at index `50834`:

```text
index=50834 class=LinkerLoad name=LinkerLoad item_dword_0x8=1001
index=50842 class=ShooterHUD name=Default__ShooterHUD item_dword_0x8=1002
index=50921 class=PaintingStreamingComponent name=PaintingStreamingComp item_dword_0x8=1003
```

The top nonzero-serial classes include `LinkerLoad`, behavior-tree composites/decorators,
and mesh components. This supports the static helper interpretation that
`FUObjectItem+0x8` is serial-backed and can hold published nonzero serials.

## Interpretation

- The old small-sample blocker `zero_or_missing_fuobjectitem_serial_candidates` is too
  broad when applied to wider object-array scans. It remains true for the earlier tiny
  sampled indices, but not for the copied cores overall.
- Nonzero serial evidence is now present in two copied cores, with matching object indices
  and internal-index checks.
- `FUObjectItem+0xc` remains unknown. Do not reinterpret it as serial evidence.
- No sampled object in the first 200,000 readable slots had `UObject+0x8` mask `0x100` or
  `0x4000`, so `uobject_flags_validity_semantics_unproven` remains a blocker.
- Public `ResourceHandle` stays blocked. Internal tooling can use this result to refine the
  next revalidation gate: serial presence is no longer the primary blocker; lifetime,
  invalidation/reuse, and flag semantics are.

## Next Step

Update the ResourceHandle evaluator to distinguish:

- `no_nonzero_serial_candidates_found`, which is now false for broad scans;
- `mixed_zero_and_nonzero_serial_candidates`, which is expected for a full object array;
- `uobject_flags_validity_semantics_unproven`, which remains the decisive blocker.

Do not expose object handles in the public ABI until a runtime-safe lifetime model and
negative flag samples are proven.
