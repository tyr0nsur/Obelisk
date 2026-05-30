# Transfer Second-Source Readiness

## Current Status

The historical ScriptStruct candidate root recorded below predates the current bool-tail
strictness. Rechecking it now leaves `PrimalLocalProfile.ArkTributePlayerData`
inconclusive because three `BoolProperty` fields lack `bool_field_size` and
`bool_byte_offset`.

Use the refreshed 2026-05-30 evidence for current local `transfer-scriptstruct`
comparisons:

- [2026-05-30-transfer-scriptstruct-booltail-refresh.md](2026-05-30-transfer-scriptstruct-booltail-refresh.md)

The UFunction second-source result in this note remains useful historical layout evidence.

## Objective

Record the first accepted offline second-source layout evidence for transfer-related
UFunctions and ScriptStructs. This is evidence for target-set layout consistency only; it
does not promote a public Transfer SDK, object identity, payload decoding, mutation,
return override, runtime hooks, or `ResourceHandle`.

## Environment

- Date: 2026-05-29
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Offline evidence root:
  `/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z`
- Source binary:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer`
- Source core:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- Core SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- FName root slot: `0x5956f30`
- GObjects candidate: `0x595b7e0`

## UFunction Result

The `transfer-ufunction-intake` target set passed second-source snapshot comparison:

```text
/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/snapshot-comparison/readiness-report.json
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
evidence_scope=second_source_layout_evidence_only
targets=7
second_source_accepted=7
second_source_missing=0
second_source_rejected=0
promotion_gate.ready=true
promotion_gate.layout_ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.promotion_ready=false
blockers=[]
```

Here `promotion_gate.ready=true` is scoped by
`evidence_scope=second_source_layout_evidence_only`,
`promotion_gate.ready_scope=layout_only`, and
`promotion_gate.promotion_ready=false`. It is not a public/runtime readiness claim, and
the accepted targets are not usable Transfer functions or plugin APIs.

Accepted targets:

```text
PrimalDinoCharacter.IsAllowedToTransfer
ShooterGameState.AllowDownloadDino
ShooterPlayerController.ServerDownloadTransferredPlayer
ShooterPlayerController.ServerTransferredPlayerConfirmationResult
ShooterPlayerController.ServerUploadCurrentCharacterAndItems
ShooterPlayerController.ServerUploadDino
ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters
```

## ScriptStruct Result

The `transfer-scriptstruct` target set passed second-source snapshot comparison:

```text
/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/scriptstruct-comparison/readiness-report.json
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
evidence_scope=second_source_layout_evidence_only
targets=2
second_source_accepted=2
second_source_missing=0
second_source_rejected=0
promotion_gate.ready=true
promotion_gate.layout_ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.promotion_ready=false
blockers=[]
```

This has the same layout-only meaning: accepted ScriptStruct targets are evidence for
offline field review, not decoded payload contracts, runtime dispatch approval, or public
Transfer SDK/API surfaces.

Accepted targets:

```text
PrimalLocalProfile.ARKTributeDino
PrimalLocalProfile.ArkTributePlayerData
```

## Redacted Signature Result

The candidate-only redacted UFunction signature artifact was generated from the
second-source snapshots and accepted by the offline artifact gate in consume mode:

```text
/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/redacted-transfer/signatures.json
schema=obelisk.redacted-ufunction-signatures.v1
sha256=ef004358a777f7c998c8f74ff9493196fd61137c5d2f1eedcad053f89a3de532

/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/redacted-transfer/consume-gate.json
schema=obelisk.offline-artifact-gate-result.v1
status=accepted
mode=consume
provenance_verified=true
blockers=[]
```

The sidecar:

```text
/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/pack/redacted-transfer/signatures.json.provenance.json
schema=obelisk.offline-artifact-provenance.v1
verified=true
artifact_kind=redacted_ufunction_signatures
```

## Reproducible Commands

```bash
RUN=/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z
BIN=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer
CORE=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core

python3 scripts/run_second_source_core_intake.py \
  --binary "$BIN" \
  --core "$CORE" \
  --pack-dir "$RUN/pack" \
  --snapshot-root "$RUN/ufunction-snapshots" \
  --verified-fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --target-set transfer-ufunction-intake \
  --execute

python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core "$CORE" \
  --evidence-pack-manifest "$RUN/pack/gobjects-sampling/manifest.json" \
  --output-root "$RUN/scriptstruct-snapshots" \
  --target-set transfer-scriptstruct \
  --write

mkdir -p "$RUN/pack/scriptstruct-comparison" "$RUN/pack/redacted-transfer"

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --candidate-root "$RUN/scriptstruct-snapshots" \
  --target-set transfer-scriptstruct \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json > "$RUN/pack/scriptstruct-comparison/readiness-report.json"

python3 scripts/build_redacted_ufunction_signatures.py \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/PrimalDinoCharacter.IsAllowedToTransfer.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterGameState.AllowDownloadDino.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterPlayerController.ServerDownloadTransferredPlayer.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterPlayerController.ServerTransferredPlayerConfirmationResult.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterPlayerController.ServerUploadCurrentCharacterAndItems.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterPlayerController.ServerUploadDino.snapshot.json" \
  --snapshot "$RUN/ufunction-snapshots/7e7ded49e0c6/sdk_transfers/ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.snapshot.json" \
  --source-target-set transfer-ufunction-intake \
  --json > "$RUN/pack/redacted-transfer/signatures.json"

python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline \
  --artifact transfer-redacted="$RUN/pack/redacted-transfer/signatures.json" \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --strict-target-set-coverage \
  --json > "$RUN/pack/redacted-transfer/consume-gate.json"
```

## Non-Claims

- No public Transfer SDK is promoted.
- No transfer payload decoding is promoted.
- No player, dino, item, tribe, class, or object identity is promoted.
- No raw params, UE pointers, object refs, lookup, mutation, return override, runtime hook,
  or `ResourceHandle` surface is promoted.
- These targets are binary-hash-scoped layout evidence for offline planning.

## Next Steps

- Keep this evidence as post-RC planning input unless a copied-scalar surface becomes
  clearly useful and privacy-safe.
- If any transfer scalar is modeled after RC, the smallest candidate is
  `ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept`: one
  `BoolProperty`, offset `0`, `ParmsSize=1`, input-only, and no object refs, class refs,
  arrays, strings, structs, IDs, or return-value capture.
- Even that candidate is not ready for runtime observation. Blockers remain:
  candidate-only redacted signatures, function flags not bound to an exact runtime gate,
  unknown property flag bits, no approved runtime observation, no transfer observer
  marker/env/budget gate, no dispatcher ownership/lifetime tests, and no copied payload
  ABI or policy decision.
- If a future transfer surface is considered, start with copied bool/scalar policy
  candidates only, require exact target gating, and keep payload structs opaque until their
  fields have independent evidence and sensitivity review.
