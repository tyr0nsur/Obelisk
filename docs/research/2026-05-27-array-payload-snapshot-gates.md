# Array Payload Snapshot Gates

## Objective

Record the first focused offline pass over array-like mission and tribe payloads, and set
the gate before adding array fixtures to the manifest.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `76cbc7a Validate enum candidates in snapshots`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used exact offline inspector lookups for previously deferred tribe and mission payloads:

- `ShooterPlayerController.ClientReceiveTribeLog`
- `ShooterPlayerController.ClientReceiveMyTribeOnlineList`
- `ShooterPlayerController.ClientReceiveActiveMissionTags`

## Evidence

| Target | Observed Property | ParmsSize | Current Fixture Decision |
| --- | --- | ---: | --- |
| `ShooterPlayerController.ClientReceiveTribeLog` | `StrProperty LogString` at offset `0x0`, size `16` | 16 | Defer as string payload, not array. |
| `ShooterPlayerController.ClientReceiveMyTribeOnlineList` | `ArrayProperty OnlinePlayerIDs` at offset `0x0`, size `16` | 16 | Defer until array inner metadata is preserved. |
| `ShooterPlayerController.ClientReceiveActiveMissionTags` | `ArrayProperty MissionTags` at offset `0x0`, size `16` | 16 | Defer until array inner metadata is preserved. |

The exact targets resolve as `Function` with candidate UObject membership and bounded
property chains. The current sanitized snapshot output records that a property is
`ArrayProperty`, but it does not preserve the array inner property shape.

## Result

Do not add array payload fixtures yet. The current output can prove a bounded `TArray`
container-shaped parameter exists, but not the element type, ownership, or safe decoding
policy. Adding these now would look more complete than the evidence actually is.

## Rejected Paths

- Treating `ClientReceiveTribeLog` as an array target: rejected; exact snapshot shows
  `StrProperty LogString`.
- Promoting `OnlinePlayerIDs` or `MissionTags` as public SDK payloads: rejected until the
  snapshot format records array inner metadata and tests validate it.

## Risks

- A `TArray` shell without inner type is not enough for decoding or ABI exposure.
- Mission tags and online lists are client payload surfaces; runtime behavior remains
  unvalidated.
- String payloads still require the existing FString ownership and sanitization gates.

## Next Steps

- Extend offline inspector snapshots to preserve sanitized `ArrayProperty` inner metadata
  when available.
- Add fixture tests for array inner metadata before manifesting array payload targets.
- Keep string payloads separate from array work so FString gates remain explicit.
