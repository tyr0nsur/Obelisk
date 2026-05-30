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

## 2026-05-30 Parameter Provenance Hardening

The internal/test-only recognizer now records borrowed parameter provenance for matched
invocations: `ParameterData=params` and `ParameterSize=ParmsSize`. Fixture tests verify
that `bAccept` resolves to `params + 0` with one byte, that metadata-only recognition does
not expose a range, and that disabled/unsupported/rejected paths clear stale provenance
without reading memory before the gate. The borrowed pointer exists only for immediate
internal validation; it must not be persisted, logged, exposed to plugins, used as object
identity, or treated as authorization for a Transfer hook or SDK.

## 2026-05-30 Next Evidence Slice

The next useful transfer step is a `transfer-baccept-only-policy-slice` offline artifact,
not hook wiring. It should narrow the broad `transfer-ufunction-intake` evidence to exactly
one copied field:

- `ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept`

The slice should fail closed unless the committed snapshot proves `FunctionFlags=0x220cc0`,
`NumParms=1`, `ParmsSize=1`, `ReturnValueOffset=0xffff`, a single `BoolProperty` named
`bAccept` at offset `0`, `ElementSize=1`, `ArrayDim=1`, byte mask `0x01`, field mask
`0xff`, and `native_bool=false`.

It must explicitly exclude spawn point ids, region indexes, player data ids, bed ids,
return bools, object refs, class refs, tribute structs, arrays, strings, ids, mutation,
return override, dispatcher wiring, runtime hook wiring, and public SDK promotion. The
artifact should remain `promotion_ready=false`.

## 2026-05-30 Offline Artifact Gate

Implemented the consume-only schema
`obelisk.transfer-baccept-only-policy-slice.v1` in
`scripts/validate_offline_artifact_gate.py`. The gate accepts only
`transfer-baccept-only-policy-slice` manifests derived from `transfer-ufunction-intake`
and pins one copied field:

- `ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept`

The manifest must keep `policy_status=evidence-only`, `snapshot_root=redacted`,
`promotion_ready=false`, complete seven-snapshot `transfer-ufunction-intake` provenance,
and the exact copied bool shape:
`FunctionFlags=0x220cc0`, `NumParms=1`, `ParmsSize=1`,
`ReturnValueOffset=0xffff`, `BoolProperty`, offset `0`, `ElementSize=1`,
`ArrayDim=1`, byte mask `0x01`, field mask `0xff`, and `native_bool=false`.

The gate also pins forbidden transfer fields so consume-mode evidence cannot silently
broaden into spawn-point, identity, return-bool, object-ref, or class-ref surfaces:

- `ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID`
- `ShooterPlayerController.ServerDownloadTransferredPlayer.spawnPointRegionIndex`
- `ShooterPlayerController.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID`
- `ShooterPlayerController.ServerRequestSpawnPointsForDownloadedCharacters.IgnoreBedID`
- `PrimalDinoCharacter.IsAllowedToTransfer.WorldContextObject`
- `PrimalDinoCharacter.IsAllowedToTransfer.ReturnValue`
- `ShooterGameState.AllowDownloadDino.TheDinoClass`
- `ShooterGameState.AllowDownloadDino.ReturnValue`
- `ShooterPlayerController.ServerUploadCurrentCharacterAndItems.InventoryComp`
- `ShooterPlayerController.ServerUploadDino.DownloadedDino`

Promotion mode is always blocked for this schema. Public/runtime overclaims are rejected
outside the required non-claims and explicit exclusions. The explicit exclusions include
tribute structs, arrays, strings, ids, object/class refs, mutation, return override,
dispatcher wiring, runtime hook wiring, and public SDK promotion.

## 2026-05-30 Durable Policy Slice

The focused Transfer `bAccept` policy slice is preserved at:

```text
/home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z/
```

Artifact checksums:

- `transfer-baccept-only-policy-slice.json`:
  `a2b0939189cb847b351c638141fa5e122c08ca69acadae8b5c86d894fc208f12`
- `consume-gate.json`:
  `0e6e05d6975472a12ab8537550a939334e84156ba4fc78f64c5542254ffdfebc`
- `promote-gate.json`:
  `70661c87f8dc8cec0c944820e2692f8b924051b33e9e71b6ade2862ca1933912`

Consume mode accepts the slice with no blockers. Promote mode blocks it with
`promote_mode_transfer_baccept_policy_slice_evidence_only` and
`promote_mode_manifest_has_non_claims`. This is the intended result: the slice is
offline/internal evidence only and does not authorize hook wiring, marker/env activation,
dispatcher callbacks, runtime logs, public Transfer SDK, identity, mutation, return
override, or payload decoding.

Use the focused policy slice above as the canonical `bAccept` evidence. Use
`/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/` only as the
broader target-set/layout evidence source: its UFunction readiness accepted `7/7`
`transfer-ufunction-intake` targets with `promotion_ready=false`, and its ScriptStruct
readiness accepted `2/2` transfer structs as layout-only evidence. Older transfer-risk
rollups without provenance sidecars or target-set coverage remain stale triage inputs, not
promotion evidence.

## Non-Claims

This note does not promote transfer to the RC, does not promote any public transfer API,
and does not change the layout-only status of the existing transfer evidence.
