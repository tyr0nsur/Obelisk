# Transfer ScriptStruct Bool-Tail Refresh

Date: 2026-05-30

## Objective

Refresh the stale `transfer-scriptstruct` second-source candidate with current
ScriptStruct snapshot tooling, preserving UE4 `BoolProperty` tail metadata for
`PrimalLocalProfile.ArkTributePlayerData`.

This is layout-only evidence. It does not promote a public Transfer SDK, payload
decoding, runtime hooks, object identity, lookup, mutation, return override,
`ResourceHandle`, or plugin-facing Transfer callbacks.

## Inputs

- Obelisk commit: `7cb1920`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Source binary:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer`
- Source core:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- Core SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- Evidence pack manifest:
  `/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/gobjects-sampling/manifest.json`
- FName root slot from manifest: `0x5956f30`
- GObjects candidate from manifest: `0x595b7e0`

Generated output root:

```text
/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z
```

Normalized inventory pack:

```text
/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack
```

## Commands

```bash
OUT=/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z
RUN=/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z
CORE=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core

python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core "$CORE" \
  --evidence-pack-manifest "$RUN/pack/gobjects-sampling/manifest.json" \
  --output-root "$OUT/scriptstruct-snapshots" \
  --target-set transfer-scriptstruct \
  --write

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --candidate-root "$OUT/scriptstruct-snapshots" \
  --target-set transfer-scriptstruct \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json > "$OUT/transfer-scriptstruct-readiness.json"

python3 scripts/build_scriptstruct_inventory_pack.py \
  --evidence-pack-manifest "$RUN/pack/gobjects-sampling/manifest.json" \
  --evidence-pack-fname-root-label verified_fname_root_slot \
  --evidence-pack-gobjects-label gobjects \
  --target-set transfer-scriptstruct \
  --include-structs \
  --output-dir "$OUT/inventory-pack"

python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts \
  --manifest "$OUT/inventory-pack/manifest.json" \
  --mode consume \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --json > "$OUT/inventory-pack/consume-gate.json"

python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts \
  --manifest "$OUT/inventory-pack/manifest.json" \
  --mode promote \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --json > "$OUT/inventory-pack/promote-gate.json"

python3 scripts/normalize_artifact_pack.py "$OUT/inventory-pack" --json
python3 scripts/normalize_artifact_pack.py "$OUT/inventory-pack" --check --json
```

## Result

The refreshed candidate accepted both `transfer-scriptstruct` targets:

```text
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
evidence_scope=second_source_layout_evidence_only
targets=2
second_source_accepted=2
second_source_inconclusive=0
second_source_missing=0
second_source_rejected=0
promotion_gate.ready=true
promotion_gate.layout_ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.promotion_ready=false
blockers=[]
```

Here `promotion_gate.ready=true` means only that the refreshed ScriptStruct layout
comparison passed with `ready_scope=layout_only` and `promotion_ready=false`. It does not
make the transfer structs decoded payload contracts or usable plugin APIs.

Accepted targets:

```text
PrimalLocalProfile.ARKTributeDino
PrimalLocalProfile.ArkTributePlayerData
```

The refreshed `ArkTributePlayerData` snapshot preserves the three bool-tail fields:

```text
bWasAllowDPCUpload: offset=272 bool_field_size=1 bool_byte_offset=0 byte_mask=0x1 field_mask=0xff native_bool=false
bWithItems:         offset=273 bool_field_size=1 bool_byte_offset=0 byte_mask=0x1 field_mask=0xff native_bool=false
bForServerTransfer: offset=280 bool_field_size=1 bool_byte_offset=0 byte_mask=0x1 field_mask=0xff native_bool=false
```

These are UE4 bitfield-style `BoolProperty` observations. Do not normalize them to
`native_bool=true`, and do not omit `bool_field_size` or `bool_byte_offset`.

## Inventory Pack Gate

The inventory pack was regenerated with `--include-structs`, so the child
`scriptstruct-inventory.json` carries the same bool-tail details instead of relying only on
the readiness report.

The offline artifact gate now treats `transfer-scriptstruct` inventory packs as
bool-tail-sensitive: consume mode requires the child inventory to include `scriptstructs`
and requires `PrimalLocalProfile.ArkTributePlayerData` to preserve
`bWasAllowDPCUpload`, `bWithItems`, and `bForServerTransfer` with exact offsets and
bool-tail metadata. This is a gate hardening only; it does not promote Transfer.

The redacted ScriptStruct signature gate now applies the same Transfer bool-tail contract
by content, not only by target-set label. If a redacted ScriptStruct report contains
`PrimalLocalProfile.ArkTributePlayerData`, the gate treats it as Transfer evidence even
when `target_sets/source_target_sets` omit `transfer-scriptstruct`, requires complete
`obelisk.redacted-scriptstruct-target-set-coverage.v1` coverage, and rejects reports that
drop any of the three exact bool-tail fields. This prevents stale or hand-edited
signature reports from bypassing the Transfer contract by losing the label.

The redacted ScriptStruct signature builder also treats both Transfer structs as payload
metadata only. Scalar and bool fields in `PrimalLocalProfile.ARKTributeDino` and
`PrimalLocalProfile.ArkTributePlayerData` are emitted as redacted Transfer payload fields,
not copied-scalar candidates, while retaining the exact bool-tail metadata needed for
offline review.

Gate result:

```text
consume-gate.json: status=accepted
promote-gate.json: status=blocked
promote blockers:
- promote_mode_scriptstruct_inventory_candidate_only
- promote_mode_manifest_has_non_claims
```

Normalization result:

```text
artifact-pack.manifest.json: present
SHA256SUMS: present
normalize --check: status=ok
file_count=5
```

## Stale Artifact Recheck

The older candidate root under:

```text
/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/scriptstruct-snapshots
```

is stale with current comparator strictness. It accepts `ARKTributeDino`, but leaves
`ArkTributePlayerData` inconclusive because those three bools lack `bool_field_size` and
`bool_byte_offset`. Use the refreshed artifact root above for current local evidence.

## Non-Claims

- No public Transfer SDK/API is promoted.
- No transfer payload decoder is promoted.
- No player, dino, item, tribe, class, or UObject identity is promoted.
- No raw params, UE pointers, object refs, lookup, mutation, return override, runtime hook,
  or `ResourceHandle` surface is promoted.
- This does not authorize server-backed Transfer runtime work.

## Next Step

If Transfer continues, keep it internal and evidence-only. The next useful step is to
harden the artifact lineage around the redacted ScriptStruct signatures generated from
this bool-tail-complete evidence. `BoolProperty` fields in redacted signatures now carry
`bool_field_size`, `bool_byte_offset`, masks, and `native_bool`, and the offline artifact
gate rejects `transfer-scriptstruct` redacted signatures unless the same three
`ArkTributePlayerData` bool contracts are present. Keep consume accepted / promote blocked
and do not add a public Transfer SDK, runtime observer, payload decoder, identity,
mutation, or return override.
