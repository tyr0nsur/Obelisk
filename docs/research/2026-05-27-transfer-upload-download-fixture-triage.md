# Transfer Upload Download Fixture Triage

## Objective

Promote compact transfer/upload/download metadata snapshots while keeping large struct,
array, and string payloads deferred.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `dd07098 Add array payload snapshot fixtures`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used exact offline inspector lookups for transfer/download/upload candidates reported by
the read-only transfer pass. Only compact scalar, object, class, and bool-return shapes
were accepted for metadata-only fixtures.

## Evidence

Accepted fixture targets:

| Target | Params | ParmsSize | Signal |
| --- | ---: | ---: | --- |
| `ShooterPlayerController.ServerDownloadTransferredPlayer` | 2 | 8 | Spawn point and region scalar metadata. |
| `ShooterPlayerController.ServerTransferredPlayerConfirmationResult` | 1 | 1 | Transfer confirmation bool. |
| `ShooterPlayerController.ServerUploadCurrentCharacterAndItems` | 1 | 8 | Inventory component object metadata. |
| `ShooterPlayerController.ServerUploadDino` | 1 | 8 | Dino object metadata. |
| `ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters` | 2 | 12 | Player data id plus ignored bed id scalars. |
| `ShooterGameState.AllowDownloadDino` | 2 | 9 | Dino class plus bool return policy shape. |
| `PrimalDinoCharacter.IsAllowedToTransfer` | 2 | 9 | Context object plus bool return policy shape. |

All accepted targets resolved as `Function` with candidate UObject membership and bounded
property chains in the inspected core.

## Result

`sdk.transfers` now has a compact metadata foothold for transfer/download/upload surfaces.
This does not imply runtime invocation safety, upload/download policy correctness, or
public SDK readiness.

## Rejected Paths

- `ShooterPlayerController.ServerRequestDownloadDino`: `StructProperty` payload around
  288 bytes; deferred.
- `ShooterPlayerController.ServerRequestDownloadPlayerCharacter`: large downloaded
  character struct plus scalar fields; deferred.
- `ServerCharacterUploadWithItems_Start`, `ServerCharacterUploadWithItems_UploadItem`,
  and `ServerCharacterUploadWithItems_CharaterPayload`: large struct or array payloads;
  deferred. Preserve the game's `Charater` spelling if these are ever documented.
- `ClientUploadedCharactersLoaded` and `ClientUploadedDinosLoaded`: array payloads;
  deferred.
- `ServerTransferAllFromRemoteInventory` and `ServerTransferAllToRemoteInventory`:
  string payloads; deferred until FString gates apply.
- `ServerRequestTransferOwnershipInMyTribe`: real compact target, but tribe ownership,
  not ARK transfer/upload/download.

## Risks

- Transfer/upload/download names are gameplay-sensitive; fixtures prove metadata shape
  only.
- Object/class params are not ownership or lifetime contracts.
- Runtime probing remains gated to TheIsland or an isolated debug instance in an approved
  window.

## Next Steps

- Keep `sdk.transfers` candidate-only and offline.
- Add struct identity evidence before any large transfer payload fixture.
- Do not expose transfer SDK callbacks until ownership, policy, and rollback gates exist.
