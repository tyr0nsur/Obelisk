# SDK Module Taxonomy

## Objective

Define a research-first module taxonomy for Obelisk so future work does not drift back to
chat-only development. This is a planning document, not a public SDK contract.

## Evidence Baseline

The current offline baseline is the general `UFunction` inventory from the existing
core/evidence pack:

- `5269` reflected `Function` objects in the first `30000` `GObjects` entries.
- Focused reports exist for:
  - `ShooterPlayerController`
  - `PrimalItem`
  - `PrimalDinoCharacter`
- Evidence is scoped to ARK Linux binary SHA256
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

## Readiness Levels

Use one ladder for every module area:

| Level | Meaning |
| --- | --- |
| `inventory` | Broad offline `UFunction` listing only. |
| `candidate` | Focused function set with resolved name, outer/class, `NumParms`, and `ParmsSize`. |
| `validated-offline` | Property chains pass target/class/outer/property `GObjects` back-reference checks. |
| `fixture-backed` | Analyzer or C++ fixtures cover accepted and rejected examples. |
| `runtime-observed` | Isolated debug validation sees the exact function with bounded params and no mutation. |
| `internal-event` | Runtime can produce copied-owned internal events behind explicit gates. |
| `public-sdk` | Append-only C ABI, ownership/lifecycle tests, installed SDK consumer tests, and docs exist. |

Do not promote a module on name proximity, one core, broad substring filters, readable
memory alone, or metadata reads without ownership and lifetime design.

## Module Map

| Module Area | Current Sources | Near-Term Purpose | Status |
| --- | --- | --- | --- |
| `sdk.chat` | `ServerSendChatMessage`, exact chat fallback recognizers | Internal observation and eventual copied-data event API | Experimental internal only |
| `sdk.player` | `ShooterPlayerController` session/client/server functions | Player identity, notifications, inventory requests, tribe requests | Candidate-only |
| `sdk.inventory` | `ServerRequestInventoryUseItem*`, `PrimalItem` use/equip/remote gates | First non-chat analyzer fixtures | Candidate-only; strongest next track |
| `sdk.items` | `PrimalItem` crafting, repair, durability, NetExec | Item metadata and policy design | Candidate-only |
| `sdk.dinos` | `PrimalDinoCharacter` passenger, carry, attack, tame, flight | Dino event metadata fixtures | Candidate-only |
| `sdk.structures` | `ServerRequestPlaceStructure`, multiuse/place functions, `PrimalStructure` | Struct-heavy validation surface | Candidate-only; defer runtime |
| `sdk.tribes` | Tribe/alliance/log request functions | Low-param observation candidates | Candidate-only |
| `sdk.transfer` | Upload/download/ARK transfer functions | Future deep struct decoding | Candidate-only; defer |
| `sdk.admin` | `ShooterCheatManager`, controller admin RPCs | Research and permission-model planning | Documentation-only |
| `ue.reflection` | `FName`, `GObjects`, `UObject`, `UFunction`, `UProperty`, `FString` | Internal substrate for every module | Not public SDK |

## Promotion Gates

Before a module can move from `candidate` to `validated-offline`:

- It must use exact or narrow filters, not broad substring matches.
- Target function, class, outer, and properties must back-reference through
  `GObjects[InternalIndex]`.
- `NumParms`, `ParmsSize`, property offsets, and element sizes must be internally
  consistent.
- Rejected examples must be recorded.

Before a module can move to `runtime-observed`:

- It needs fixture coverage.
- The run must target TheIsland or a dedicated debug instance during an explicit approved
  window.
- Ragnarok must remain untouched unless the operator explicitly opens maintenance.
- The runtime path must be observation-only and bounded by reflected `ParmsSize`.

Before a module can move to `public-sdk`:

- Runtime events must copy all data they expose.
- No public API may expose raw `UObject*`, `UFunction*`, property-chain pointers,
  borrowed `FString` buffers, offsets, or core-only addresses.
- The ABI must remain append-only and include ownership/lifecycle tests.
- Installed SDK consumer tests must pass.

## Candidate-Only Surfaces

Keep these out of public SDK until stronger evidence and policy exist:

- Admin commands and cheat-manager functions.
- Upload/download/transfer functions.
- Structure placement and large transform-heavy calls.
- Item NetExec command surfaces.
- Raw Blueprint hooks.
- Generic `UFunction` invocation helpers.
- Public object iteration over raw UE objects.

## First Fixture Targets

Prioritize compact, non-chat property chains:

```text
ShooterPlayerController.ServerRequestInventoryUseItem
PrimalItem.AllowRemoteAddToInventory
PrimalItem.CanUse
PrimalItem.UseItemOntoItem
PrimalDinoCharacter.AddPassenger
PrimalDinoCharacter.AllowCarryCharacter
PrimalDinoCharacter.ServerRequestAttack
PrimalDinoCharacter.SetCharacterStatusTameable
```

Structure placement should remain a later fixture because it exercises larger struct-heavy
params and has higher gameplay-authority risk.

## Open Questions

- Which compact non-chat candidate should become the first analyzer fixture?
- Should module readiness be tracked in one central table or inside each focused research
  note?
- What minimum second-source evidence is required before non-chat runtime observation?
- What policy layer is needed before admin, transfer, and NetExec surfaces can be discussed
  as SDK features?

## Source Notes

- `docs/research/2026-05-27-general-ufunction-inventory.md`
- `docs/research/2026-05-27-shooterplayercontroller-function-inventory.md`
- `docs/research/2026-05-27-primalitem-function-inventory.md`
- `docs/research/2026-05-27-primaldinocharacter-function-inventory.md`
