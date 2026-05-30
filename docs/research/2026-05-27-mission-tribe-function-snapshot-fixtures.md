# Mission And Tribe Function Snapshot Fixtures

## Objective

Broaden gameplay fixture coverage with compact mission lifecycle and tribe permission
UFunction snapshots.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `43b1054 Add structure function snapshot fixtures`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used exact offline inspector lookups for mission and tribe targets recommended by the
prior read-only review:

- `MissionType.BPAllowPlayerToLeaveMission`
- `MissionType.BPOnPlayerRemovedFromMission`
- `ShooterPlayerController.AllowTribeGroupPermission`
- `ShooterPlayerController.IsInTribe`

## Evidence

Accepted fixture targets:

| Module | Target | Params | ParmsSize | Signal |
| --- | --- | ---: | ---: | --- |
| `sdk.missions` | `MissionType.BPAllowPlayerToLeaveMission` | 2 | 9 | Player object plus bool return for leave-policy metadata. |
| `sdk.missions` | `MissionType.BPOnPlayerRemovedFromMission` | 4 | 18 | Player/controller object refs plus mission-complete and phase-success bools. |
| `sdk.tribes` | `ShooterPlayerController.AllowTribeGroupPermission` | 3 | 17 | `ByteProperty` enum candidate, target object, bool return. |
| `sdk.tribes` | `ShooterPlayerController.IsInTribe` | 1 | 1 | Minimal bool-return tribe membership query. |

All four exact targets resolved as `Function` with candidate UObject membership and
bounded property chains in the inspected core.

## Result

`sdk.missions` now covers add, leave, and removal lifecycle metadata. `sdk.tribes` now
has more than the zero-param tribe-log control: it includes a compact permission enum
shape and a membership bool-return query. These remain offline metadata fixtures only.

## Rejected Paths

- `ClientReceiveTribeLog`, `ClientReceiveMyTribeOnlineList`, and
  `ClientReceiveActiveMissionTags`: real but array payloads should wait for array decoding
  policy.
- `ServerRequestMyTribeOnlineList` and `ServerRequestUpdateActiveMissionTags`: valid
  zero-param server requests, but they add less shape coverage than permission/membership.
- Mission string or tag payload targets: deferred until string/array gates are explicit.

## Risks

- The tribe permission enum values are metadata evidence, not an accepted public enum
  contract.
- Mission lifecycle names describe gameplay intent, but no runtime behavior is validated.
- Runtime probing remains gated to the currently approved debug/development target or an
  isolated debug instance in an approved window.

## Next Steps

- Regenerate fixtures from the manifest and validate exact path coverage.
- Consider a focused array/enum evidence pass before promoting tribe logs or mission tag
  payloads.
- Keep gameplay-authoritative mutations out of public SDK work until ownership and policy
  gates are documented.
