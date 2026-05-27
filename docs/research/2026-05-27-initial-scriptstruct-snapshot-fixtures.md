# Initial ScriptStruct Snapshot Fixtures

## Objective

Add the first manifest-backed ScriptStruct fixtures using the dedicated ScriptStruct
fixture root and regeneration tooling.

## Environment

- ScriptStruct manifest:
  `tests/fixtures/scriptstruct_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `0e11b07 Add ScriptStruct snapshot regeneration tooling`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Added two transfer-adjacent ScriptStruct targets under `sdk_transfers`:

- `PrimalLocalProfile.ARKTributeDino`
- `PrimalLocalProfile.ArkTributePlayerData`

Generated snapshots with `scripts/regenerate_scriptstruct_snapshots.py`.

## Evidence

| Struct | PropertiesSize | Observed Fields | High-Risk Shapes |
| --- | ---: | ---: | --- |
| `ARKTributeDino` | 288 | 10 | Strings, byte array, class ref, scalar IDs/stats. |
| `ArkTributePlayerData` | 288 | 11 | Byte array, strings, bool flags, scalar IDs/version. |

Both snapshots use schema `obelisk.scriptstruct-chain.snapshot.v1`, inspection mode
`script_struct`, and sanitized property chains.

## Result

`sdk_transfers` now has candidate-only ScriptStruct field evidence for dino and player
tribute payload shapes. This does not decode payload buffers, establish ownership, or
permit runtime dispatch.

## Rejected Paths

- `ItemNetInfo`: deferred as the first ScriptStruct fixture wave because it has 62 fields,
  nested arrays of structs, class refs, weak object refs, and bitfield-heavy regions.
- Any runtime transfer/upload/download dispatch: rejected.

## Risks

- Field names and offsets are single-core metadata candidates.
- Strings and byte arrays need separate decoding and ownership gates.
- Transfer payloads are gameplay-sensitive and must remain offline.

## Next Steps

- Add second-source validation for ScriptStruct field layouts.
- Consider `ItemNetInfo` only after nested struct/array policy is explicit.
