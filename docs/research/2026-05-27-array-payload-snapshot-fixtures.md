# Array Payload Snapshot Fixtures

## Objective

Add metadata-only UFunction snapshots for compact `ArrayProperty` payloads after the
inspector started preserving sanitized array inner metadata.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `8820707 Preserve array inner metadata in snapshots`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used exact offline inspector lookups for compact array-bearing functions recommended by
the read-only array pass:

- `PrimalInventoryComponent.InventoryCustomFilter`
- `MissionType.GetPlayerUsableItems`
- `ShooterPlayerController.ClientReceiveMyTribeOnlineList`
- `ShooterPlayerController.ClientReceiveActiveMissionTags`

## Evidence

| Module | Target | Params | ParmsSize | Array Inner Evidence |
| --- | --- | ---: | ---: | --- |
| `sdk.inventory` | `PrimalInventoryComponent.InventoryCustomFilter` | 2 | 32 | `UnfilteredItemsList` and `FilteredItemsList` inner candidates resolve as `ObjectProperty`. |
| `sdk.missions` | `MissionType.GetPlayerUsableItems` | 2 | 24 | `OutItemIDs` inner candidate resolves as `StructProperty`. |
| `sdk.tribes` | `ShooterPlayerController.ClientReceiveMyTribeOnlineList` | 1 | 16 | `OnlinePlayerIDs` inner candidate resolves as `UInt32Property`. |
| `sdk.tribes` | `ShooterPlayerController.ClientReceiveActiveMissionTags` | 1 | 16 | `MissionTags` inner candidate resolves as `NameProperty`. |

All four exact targets resolved as `Function` with candidate UObject membership, bounded
property chains, and sanitized `array_inner_candidate` entries.

## Result

The manifest now includes compact array-bearing fixtures as metadata evidence. These
fixtures prove reflected parameter shape and inner property identity only. They do not
prove `TArray` ownership, allocation behavior, element lifetime, runtime safety, or public
SDK decoding.

## Rejected Paths

- `ShooterPlayerController.ClientReceiveTribeLog`: exact snapshot shows `StrProperty
  LogString`, so it remains under string/FString gates rather than array work.
- `MissionType.SpawnMissionDinoGroupExtended`: deferred because it mixes many fields,
  gameplay-authoritative spawn behavior, and array return metadata.
- Large transfer/upload arrays: deferred until transfer struct/string/array policies are
  documented separately.

## Risks

- Inner property class names are candidate metadata from one binary hash.
- `StructProperty` array elements still need struct identity and field reconstruction
  before decoding.
- Client receive surfaces are not safe runtime dispatch targets.

## Next Steps

- Keep array fixtures candidate-only and offline.
- Add transfer compact scalar/object fixtures separately from array and struct payloads.
- Require second-source evidence before any array payload becomes public SDK data.
