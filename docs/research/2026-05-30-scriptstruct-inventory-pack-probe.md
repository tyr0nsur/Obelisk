# ScriptStruct Inventory Pack Probe

## Objective

Validate the new candidate-only `scripts/build_scriptstruct_inventory_pack.py` path against
real offline transfer evidence without touching live ARK servers or writing under
`/servidor/ark`.

## Environment

- Obelisk commit: `bde865b Add ScriptStruct inventory pack tooling`
- Source manifest:
  `/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/gobjects-sampling/manifest.json`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- FName root slot label/address: `verified_fname_root_slot` / `0x5956f30`
- GObjects label/address: `gobjects` / `0x595b7e0`
- Output probe: `local/obelisk-scriptstruct-inventory-probe/` (ignored by Git)
- Archived pack: `/servidor/ark/workspace-offline/scriptstruct-inventory-pack-transfer-20260530T012234Z`
- Server posture: no server start, restart, marker edit, ptrace/gcore, scanner, or live
  observation was performed.

## Command

```bash
python3 scripts/build_scriptstruct_inventory_pack.py \
  --evidence-pack-manifest /servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/gobjects-sampling/manifest.json \
  --evidence-pack-fname-root-label verified_fname_root_slot \
  --evidence-pack-gobjects-label gobjects \
  --target-set transfer-scriptstruct \
  --include-structs \
  --output-dir local/obelisk-scriptstruct-inventory-probe
```

Consume-mode artifact-gate check:

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/Obelisk/local \
  --protected-root /servidor/ark \
  --manifest /home/flowcommunity-ark/Obelisk/local/obelisk-scriptstruct-inventory-probe/manifest.json \
  --mode consume \
  --json
```

After archival, the same gate was rerun under `/servidor/ark/workspace-offline` with
`--expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
Both consume checks returned `status=accepted`.

## Evidence

- Pack schema: `obelisk.scriptstruct-inventory-pack.v1`
- Pack status: `candidate-only`
- Promotion status: `not_promoted_candidate_only`
- FName readiness: `ready=true`, `exact_match_count=4`
- Target set: `transfer-scriptstruct`
- Requested/matched/missing/ambiguous: `2/2/0/0`
- Artifact gate: accepted in consume mode.
- Archived manifest records child artifact hashes:
  - `scriptstruct-inventory.json`:
    `680531c0cfa9ae02ca50e221b948287c12a9c9abb7113b869ab44cbf9dd993eb`
  - `fname-root-validation.json`:
    `0d2fd0dd701c2231f70192a79487fdd8f4e4de40aed064d2e7c0ef42d5d80ace`

Inventory summary:

- `scriptstruct_count=2`
- `candidate_count=2`
- `rejected_count=0`
- Top property classes:
  - `StrProperty=8`
  - `FloatProperty=3`
  - `UInt32Property=3`
  - `BoolProperty=3`
  - `ArrayProperty=2`
  - `ClassProperty=1`
  - `UInt64Property=1`

Targets:

- `PrimalLocalProfile.ARKTributeDino`
  - `properties_size=288`
  - `observed_property_count=10`
  - first fields include `DinoClassName`, `DinoClass`, `DinoData`,
    `DinoName`, `DinoNameInMap`, `DinoStats`, `DinoExperiencePoints`, and
    `Version`
- `PrimalLocalProfile.ArkTributePlayerData`
  - `properties_size=288`
  - `observed_property_count=11`
  - first fields include `PlayerDataID`, `PlayerDataBytes`, `PlayerName`,
    `PlayerStats`, `UploadingServerMapName`, `UploadingServerName`,
    `bWasAllowDPCUpload`, and `bWithItems`

## Result

Confirmed: the ScriptStruct inventory pack can consume existing offline evidence-pack
inputs and produce target-set-complete, redacted, candidate-only inventory rows for the
transfer ScriptStruct set. This is useful planning evidence for post-RC transfer/resource
modeling.

This does not replace the existing transfer second-source readiness report. The prior
readiness report remains the source for layout-only comparison status; this pack adds a
more convenient offline inventory/review artifact.

## Non-Claims

- Does not promote public ScriptStruct, Transfer, Inventory, Items, or Resources SDKs.
- Does not decode transfer payloads.
- Does not expose UE pointers, raw params, FName/GObjects indices, object identity, lookup,
  or `ResourceHandle`.
- Does not authorize mutation, return override, ProcessEvent blocking, or UE call replay.
- Does not prove runtime safety or cross-binary portability.

## Risks

- The initial local output is ignored by Git; the validated pack is archived under
  `/servidor/ark/workspace-offline/scriptstruct-inventory-pack-transfer-20260530T012234Z`.
- Some fields are high-risk identity or payload fields (`PlayerDataID`, arrays, class refs,
  text/stats) and must remain redacted or planning-only until separate copied-data,
  privacy, lifecycle, and ABI gates exist.
- Artifact gate consume mode validates schema/path/non-claim hygiene, not public SDK
  promotion.

## Next Steps

1. Add a redacted rollup builder or report path if repeated ScriptStruct inventory packs
   become common.
2. Use this evidence to refine post-RC transfer copied-scalar feasibility; likely copied
   bools remain the only near-term safe transfer signal.
3. Keep public RC work focused on the existing copied `GameplayPolicyEvent` and
   `ChatMessageEvent` surfaces.
