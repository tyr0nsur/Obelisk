# ArkTributePlayerData Identity Boundary

Date: 2026-05-31

## Scope

Record the safe boundary for `PrimalLocalProfile.ArkTributePlayerData` after the transfer
ScriptStruct refresh. This is an identity-risk orientation note only. It does not promote
player identity, transfer payload decoding, runtime hooks, `ResourceHandle`, lookup,
permissions, commands, persistence, mutation, return override, or public SDK surface.

## Evidence

Artifact root:

```text
/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z
```

Snapshot:

```text
scriptstruct-snapshots/7e7ded49e0c6/sdk_transfers/PrimalLocalProfile.ArkTributePlayerData.snapshot.json
```

Relevant evidence facts:

- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Snapshot schema: `obelisk.scriptstruct-chain.snapshot.v1`.
- Snapshot evidence status: `candidate-only`.
- Readiness schema: `obelisk.reflection-snapshot-readiness.v1`.
- Transfer ScriptStruct readiness has `second_source_status=compared`, `targets=2`,
  `second_source_accepted=2`, and `promotion_gate.ready_scope=layout_only`.
- Inventory-pack promote gate is blocked by
  `promote_mode_scriptstruct_inventory_candidate_only` and
  `promote_mode_manifest_has_non_claims`.

## Observed Layout-Risk Fields

`ArkTributePlayerData` has `properties_size=288` and 11 observed candidate properties.
Identity/payload-sensitive examples include:

| Field | Class | Offset | Boundary |
| --- | --- | ---: | --- |
| `PlayerDataID` | `UInt64Property` | `8` | identity-like scalar; forbidden for public identity until a separate principal contract exists |
| `PlayerDataBytes` | `ArrayProperty` of `ByteProperty` | `16` | opaque payload; no decoding or SDK exposure |
| `PlayerName` | `StrProperty` | `32` | player text/name; private/redacted |
| `PlayerStats` | `StrProperty[12]` | `48` | player payload array; private/redacted |
| `UploadingServerMapName` | `StrProperty` | `240` | server/cross-instance context; private/redacted |
| `UploadingServerName` | `StrProperty` | `256` | server/cross-instance context; private/redacted |
| `ItemCount` | `UInt32Property` | `276` | transfer payload metadata; not inventory identity or mutation |

The three bool-tail fields preserve canonical bool metadata, but they remain transfer
layout evidence only:

- `bWasAllowDPCUpload` at offset `272`
- `bWithItems` at offset `273`
- `bForServerTransfer` at offset `280`

Each is `BoolProperty`, `bool_field_size=1`, `bool_byte_offset=0`,
`byte_mask=0x1`, `field_mask=0xff`, and `native_bool=false`.

## Decision

Use this artifact as a negative boundary and orientation input for future player identity
work. It is useful because it names and locates identity-risk fields, but it does not
prove runtime player identity semantics or correlate a player with controller,
player-state, Steam/EOS/UniqueNetId, permissions, chat sender, economy principal, or
cluster identity.

The player-identity route still requires, in order:

1. A complete non-protected `obelisk.core-dump-evidence-pack.v1`.
2. A complete `obelisk.reflection-inventory-pack.v1` for the full
   `players-identity-lifecycle-intake` target set, linked through
   `inputs.evidence_pack_manifest`.
3. Focal snapshots for `ShooterPlayerController.ServerListPlayers` and
   `ShooterPlayerController.ServerKickPlayer`.
4. Candidate lifecycle anchors, privacy/invalidation policy, and independent second
   source evidence.

## Rejected Shortcuts

- Do not treat ScriptStruct inventory as a UFunction reflection inventory pack.
- Do not use `ArkTributePlayerData.PlayerDataID` as public player identity.
- Do not expose `PlayerName`, `PlayerDataBytes`, stats, server names, arrays, strings,
  or ids through public ABI.
- Do not infer `ResourceHandle`, lookup, cross-event correlation, transfer SDK,
  inventory SDK, permissions, commands, or runtime identity from this layout.
- Do not run server, ReflectionScanner, ptrace, or `gcore` from this note.

