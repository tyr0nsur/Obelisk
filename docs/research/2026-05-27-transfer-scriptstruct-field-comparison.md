# Transfer ScriptStruct Field Comparison

## Objective

Compare the first ScriptStruct-mode outputs for deferred transfer payload structs and
decide whether to add committed ScriptStruct fixtures immediately.

## Environment

- Tool:
  `scripts/inspect_core_ufunctions.py --inspection-mode script-struct --snapshot-json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `016778a Add transfer ScriptStruct snapshot fixtures`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Generated sanitized ScriptStruct snapshots for:

- `ARKTributeDino`
- `ArkTributePlayerData`
- `ItemNetInfo`

The first pass compared the three transfer payload structs. A later guarded pass added
manifest-backed fixtures for the two 288-byte tribute structs only.

## Evidence

| Struct | PropertiesSize | Observed Fields | High-Risk Shapes |
| --- | ---: | ---: | --- |
| `ARKTributeDino` | 288 | 10 | `StrProperty`, `ArrayProperty` of bytes, `ClassProperty`, scalar IDs/stats. |
| `ArkTributePlayerData` | 288 | 11 | `ArrayProperty` of bytes, multiple `StrProperty` fields, bool flags, IDs, version. |
| `ItemNetInfo` | 432 | 62 | Nested `StructProperty`, many bool bitfields sharing offsets, strings, arrays of structs, weak object, class refs, location `Vector`, egg metadata. |

The new mode records `obelisk.scriptstruct-chain.snapshot.v1` with `inspection_mode:
script_struct`, `properties_size`, and sanitized property chains. It also preserves
`array_inner_candidate` and `struct_type_candidate` for nested metadata when available.

## Result

`ARKTributeDino` and `ArkTributePlayerData` now have committed, manifest-backed
ScriptStruct fixtures under `tests/fixtures/scriptstruct_snapshots/`. They remain
candidate-only field metadata from one offline core. `ItemNetInfo` remains deferred.

## Rejected Paths

- Adding `ItemNetInfo` as a first committed ScriptStruct fixture: rejected because it has
  62 fields and multiple nested high-risk property classes.
- Treating `ARKTributeDino` or `ArkTributePlayerData` as decoded transfer payloads:
  rejected; they include strings and byte arrays.
- Mixing ScriptStruct snapshots into the existing UFunction manifest: rejected because the
  schemas differ.

## Risks

- ScriptStruct field names and offsets are still single-core candidate metadata.
- Bool bitfield semantics are not reconstructed.
- Arrays, strings, nested structs, weak/object refs, and class refs need separate ownership
  rules before SDK exposure.

## Next Steps

- Add second-source validation for `ARKTributeDino` and `ArkTributePlayerData` before
  runtime decoding or SDK promotion.
- Keep `ItemNetInfo` out of fixtures until nested array/struct and weak/object reference
  policy is explicit.
- Keep transfer payload runtime dispatch blocked.
