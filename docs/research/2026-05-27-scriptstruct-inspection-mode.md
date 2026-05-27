# ScriptStruct Inspection Mode

## Objective

Add an offline `ScriptStruct` inspection mode so large transfer payload structs can be
studied through `UStruct` metadata without treating them as `UFunction` parameter lists.

## Environment

- Tool:
  `scripts/inspect_core_ufunctions.py`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `1d72c02 Document transfer struct identity gates`
- Source:
  offline core and synthetic unit fixtures.
- Live-server impact: none.

## Method

The inspector now supports `--inspection-mode auto|ufunction|script-struct`.

- `auto` keeps existing function behavior while selecting `script_struct` for exact
  `ScriptStruct` targets.
- `script-struct` rejects non-`ScriptStruct` targets.
- `ufunction` rejects non-`Function` targets.
- Sanitized `--snapshot-json` rejects mixed function/struct target sets.

For `ScriptStruct` targets, the property walker uses:

- `UStruct.children` at offset `0x38`,
- `UStruct.properties_size` at offset `0x40`,
- no `UFunction.NumParms` expected count.

## Evidence

Synthetic tests cover a minimal `ARKTributeDino` struct with two fields and UFunction
offsets left unset, proving the struct path is using `UStruct` metadata.

Real-core exact inspection of `ARKTributeDino` emits:

- schema `obelisk.scriptstruct-chain.snapshot.v1`,
- `inspection_mode: script_struct`,
- `properties_size: 288`,
- 10 bounded fields, including string, class, array, float, and integer property shapes.

## Result

Large transfer payloads are still deferred, but the next investigation can now collect
field-level struct evidence without overloading the UFunction snapshot schema.

## Rejected Paths

- Mixed function and ScriptStruct sanitized snapshots: rejected because they need separate
  schemas.
- Treating `StructProperty` objects as standalone struct layouts: rejected; only targets
  with class `ScriptStruct` enter struct mode.

## Risks

- `ScriptStruct` field evidence is still one-core candidate metadata.
- Strings, arrays, nested structs, bitfields, and object/class refs still need ownership
  and decoding gates before SDK exposure.

## Next Steps

- Add dedicated ScriptStruct fixtures for `ARKTributeDino`, `ArkTributePlayerData`, and
  `ItemNetInfo` only after deciding their fixture root and manifest schema.
- Keep transfer runtime dispatch blocked.
