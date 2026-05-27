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
| `ShooterPlayerController.ClientReceiveMyTribeOnlineList` | `ArrayProperty OnlinePlayerIDs` at offset `0x0`, size `16`; inner candidate `UInt32Property` | 16 | Eligible for metadata-only fixture after inner metadata support lands. |
| `ShooterPlayerController.ClientReceiveActiveMissionTags` | `ArrayProperty MissionTags` at offset `0x0`, size `16`; inner candidate `NameProperty` | 16 | Eligible for metadata-only fixture after inner metadata support lands. |

The exact targets resolve as `Function` with candidate UObject membership and bounded
property chains. The first pass showed that sanitized snapshot output did not preserve
`ArrayProperty.Inner`; the follow-up inspector change now records a sanitized inner
property summary without addresses.

## Result

Do not promote array payloads to SDK behavior. With sanitized inner metadata available,
small array payload fixtures can be added as metadata-only evidence, but they still do not
prove ownership, allocation, element decoding, or runtime dispatch safety.

## Rejected Paths

- Treating `ClientReceiveTribeLog` as an array target: rejected; exact snapshot shows
  `StrProperty LogString`.
- Promoting `OnlinePlayerIDs` or `MissionTags` as public SDK payloads: rejected until
  ownership, element decoding, and second-source validation exist.

## Risks

- A `TArray` shell and inner type summary are still not enough for decoding or ABI exposure.
- Mission tags and online lists are client payload surfaces; runtime behavior remains
  unvalidated.
- String payloads still require the existing FString ownership and sanitization gates.

## Next Steps

- Add fixture tests for array inner metadata before manifesting array payload targets.
- Add metadata-only fixtures for the compact online-list and mission-tag targets after
  tool support is committed.
- Keep string payloads separate from array work so FString gates remain explicit.
