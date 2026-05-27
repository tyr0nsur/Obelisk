# Transfer Struct Identity Gates

## Objective

Record the first offline pass after adding sanitized `StructProperty` type metadata, and
keep large transfer payloads deferred until field-level reconstruction exists.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `763ba2e Preserve struct type metadata in snapshots`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used exact offline inspector lookups for deferred large transfer/upload/download payloads:

- `ShooterPlayerController.ServerRequestDownloadDino`
- `ShooterPlayerController.ServerRequestDownloadPlayerCharacter`
- `ShooterPlayerController.ServerCharacterUploadWithItems_Start`
- `ShooterPlayerController.ServerCharacterUploadWithItems_UploadItem`

## Evidence

| Target | Struct Property | Size | Sanitized Type Candidate | Decision |
| --- | --- | ---: | --- | --- |
| `ServerRequestDownloadDino` | `DownloadedDino` | 288 | `ScriptStruct ARKTributeDino` | Defer field decoding. |
| `ServerRequestDownloadPlayerCharacter` | `DownloadedCharacter` | 288 | `ScriptStruct ArkTributePlayerData` | Defer field decoding. |
| `ServerCharacterUploadWithItems_Start` | `PlayerData` | 288 | `ScriptStruct ArkTributePlayerData` | Defer field decoding. |
| `ServerCharacterUploadWithItems_UploadItem` | `InvItem` | 432 | `ScriptStruct ItemNetInfo` | Defer field decoding. |

All exact targets resolved as `Function` with candidate UObject membership and bounded
property chains. The inspector now records sanitized `struct_type_candidate` entries
without absolute addresses.

## Result

Struct identity is now visible, but large payloads remain unsafe for public SDK or runtime
dispatch. The next gate is a `ScriptStruct` inspection mode that walks `UStruct.children`
and uses `UStruct.properties_size` instead of `UFunction` `NumParms`/`ParmsSize`.
Field-level reconstruction still needs bounds, ownership, and second-source validation.

## Rejected Paths

- Adding large transfer struct snapshots as SDK-ready evidence: rejected. Type identity
  alone is not layout reconstruction.
- Decoding `ItemNetInfo` or tribute structs from runtime buffers: rejected until nested
  fields are reconstructed and tested offline.

## Risks

- Struct names and sizes are candidate metadata from one binary hash.
- A 288 or 432 byte payload can contain nested arrays, object refs, strings, or versioned
  fields that need separate ownership rules.
- Transfer/upload paths are gameplay-sensitive and must stay out of runtime work.

## Next Steps

- Regenerate existing snapshot fixtures so committed `StructProperty` entries keep
  sanitized type candidates.
- Add a `ScriptStruct` inspection path before adding large transfer payload fixtures.
- Build a struct-field inventory for `ARKTributeDino`, `ArkTributePlayerData`, and
  `ItemNetInfo` with that struct mode.
- Keep transfer runtime dispatch blocked until rollback and policy gates are explicit.
