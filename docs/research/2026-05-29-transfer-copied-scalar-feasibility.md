# Transfer Copied-Scalar Feasibility

Date: 2026-05-29

## Scope

Record the post-RC feasibility model for transfer-related reflected targets after the
accepted layout-only `transfer-ufunction-intake` and `transfer-scriptstruct` second-source
evidence. This is planning input only, not an RC public API proposal.

## Decision Matrix

| Target | Decision | Reason |
| --- | --- | --- |
| Public Transfer SDK for RC | No-go | Transfer remains outside the core-first RC. Current evidence is layout-only and does not promote payload decoding, identity, hooks, mutation, return override, `ResourceHandle`, or a public SDK. |
| `ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept` | Go, post-RC internal candidate only | Cleanest copied-scalar candidate: one non-native bool at offset `0`, `ParmsSize=1`, no refs, classes, arrays, strings, structs, ids, or return capture. |
| `ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID` / `spawnPointRegionIndex` | Maybe, post-RC research | Pure `IntProperty` scalars at offsets `0` and `4`, but spawn-point semantics may reveal location or flow choices. Requires privacy/utility review before dispatch. |
| `PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue` | Maybe, post-RC research | Copied bool return at offset `8`, but paired with `WorldContextObject:ObjectProperty`; only possible as post-original copied return bool with object redacted and no return override. |
| `ShooterGameState.AllowDownloadDino.ReturnValue` | Maybe, post-RC research | Copied bool return at offset `8`, but paired with `TheDinoClass:ClassProperty`; class identity must remain redacted. |
| `ServerUploadCurrentCharacterAndItems` / `ServerUploadDino` | No-go | Object refs only (`InventoryComp`, `DownloadedDino`); metadata-only/redacted. |
| `ServerRequestSpawnPointsForDownloadedCharacters` | No-go for copied fields now | `PlayerDataID` is identity and `IgnoreBedID` is likely identity/location-sensitive. |
| `ARKTributeDino` / `ArkTributePlayerData` ScriptStruct payloads | No-go for recognizer payload decoding | Layout evidence exists, but payloads contain names, byte arrays, ids, class refs, stats, and server names. Even scalar-looking fields require independent evidence and sensitivity review. |

## Required Evidence Before Any Internal Recognizer

1. Keep the first recognizer scope to `transfer-ufunction-intake`; do not use
   `transfer-scriptstruct` for runtime payload decoding.
2. Add fixture-backed accept/reject tests for exact outer/name, `FunctionFlags`,
   `ParmsSize`, `NumParms`, `ReturnValueOffset`, property order, type, offset, size,
   flags, bool masks, and absence of forbidden fields.
3. Bind any runtime gate to the exact supported SHA plus exact function flags.
4. Require an approved runtime observation before hook wiring: default-off marker/env,
   positive budget, exact FName prefilter before budget reservation, no raw params, and no
   object/class/string/array/id logging.
5. For return bool candidates, observe post-original only; no return override.
6. Add dispatcher ownership/lifetime tests before any copied event leaves the recognizer.

## Recommendation

After RC, start with a fixture-only `ue/TransferReflection` recognizer slice for
`ServerTransferredPlayerConfirmationResult.bAccept` only.

Do not add a hook, dispatcher, public Transfer SDK, struct payload decoder, identity, or
return override in that first slice.

## 2026-05-30 Fixture Hardening

The internal/test-only `ue/TransferReflection` slice now validates the exact copied-scalar
candidate observed in the sanitized transfer UFunction snapshot:

- `ServerTransferredPlayerConfirmationResult` object index `10494`, `Function` class object
  index `518`, and `ShooterPlayerController` outer object index `50`.
- `bAccept` property object index `10495`, `BoolProperty` class object index `532`,
  `Offset_Internal=0`, `ElementSize=1`, `ArrayDim=1`, `ParmsSize=1`, and property flags
  `0x1040000280`.
- `UBoolProperty` tail bytes at `+0x70..+0x73`: field size `0x01`, byte offset `0x00`,
  byte mask `0x01`, field mask `0xff`, and `native_bool=false`.

The exact object indices are metadata-recognition guards only, not gameplay/resource
identity. The tests still expose only a one-byte parameter range for the matched field.
They do not add runtime hook wiring, a dispatcher, mutation, return override, public ABI,
or server observation.

## Non-Claims

This note does not promote transfer to the RC, does not promote any public transfer API,
and does not change the layout-only status of the existing transfer evidence.
