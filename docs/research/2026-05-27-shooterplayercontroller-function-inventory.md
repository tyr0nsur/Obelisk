# ShooterPlayerController Function Inventory

## Objective

Use the general offline `UFunction` inventory to move Obelisk roadmap work across the full modding surface and
identify high-value player/controller function families for future reflection and SDK
planning.

## Environment

- Evidence pack:
  `/servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Instance source: existing offline core/evidence pack only.
- Live-server impact: none. No restart, attach, scanner, marker change, or runtime probe.

## Method

The focused inventory was generated with:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z \
  --max-objects 30000 \
  --outer-contains ShooterPlayerController \
  --max-groups 20 \
  --include-functions \
  --json
```

Selected gameplay candidates were then inspected with:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --outer-contains ShooterPlayerController \
  --name-contains ServerRequestInventoryUseItem \
  --name-contains ServerRequestPlaceStructure \
  --name-contains ServerRequestDinoCharStats \
  --name-contains ServerRequestTribeLog \
  --json
```

## Evidence

`ShooterPlayerController` has `435` reflected functions in the first `30000` `GObjects`
entries. The largest families are:

```text
Server:119
Client:116
On:26
Get:22
Is:18
Start:16
End:14
Set:13
BP:6
```

Useful gameplay clusters:

```text
admin:15
inventory/item/remote:97
upload/download/transfer/ark:80
tribe/alliance:11
dino/taming:22
structure/multiuse/place:14
notification/message/dialog:39
```

Representative candidates:

| Area | Candidate | Params | ParmsSize | Notes |
| --- | --- | ---: | ---: | --- |
| Admin | `ServerListPlayers` | 0 | 0 | Admin/server command surface; high policy risk. |
| Admin | `ServerKickPlayer` | 2 | 32 | Requires strict permission and ownership design before any runtime use. |
| Inventory | `ServerRequestInventoryUseItem` | 2 | 16 | Small reflected chain, good offline layout target. |
| Inventory | `ServerRequestInventoryUseItemWithActor` | 4 | 28 | Actor + item interaction candidate. |
| Inventory | `ServerRequestInventoryUseItemWithTransform` | 3 | 64 | Includes transform-sized struct param. |
| Structure | `ServerRequestPlaceStructure` | 13 | 88 | Rich placement surface; useful for property reconstruction, not first runtime hook. |
| Dino | `ServerRequestDinoCharStats` | 1 | 8 | Small dino object param, good next property-chain fixture. |
| Tribe | `ServerRequestTribeLog` | 0 | 0 | Low-param observation candidate for event identification. |
| Transfer | `ServerRequestDownloadDino` | 1 | 288 | Larger struct candidate; defer until struct decoding is stronger. |
| Client RPC | `ClientReceiveDinoCharStats` | 3 | 40 | Client-facing counterpart candidate for metadata correlation. |

The selected deeper inspection produced candidate property chains with direct UObject,
class, and outer membership back-references:

```text
ServerRequestDinoCharStats: 1/1 properties
  theDinoChar ObjectProperty offset 0x0 element 8

ServerRequestInventoryUseItem: 2/2 properties
  InventoryComp ObjectProperty offset 0x0 element 8
  ItemId StructProperty offset 0x8 element 8

ServerRequestInventoryUseItemWithActor: 4/4 properties
  anActor ObjectProperty offset 0x0 element 8
  InventoryComp ObjectProperty offset 0x8 element 8
  ItemID1 StructProperty offset 0x10 element 8
  AdditionalData IntProperty offset 0x18 element 4

ServerRequestInventoryUseItemWithTransform: 3/3 properties
  InventoryComp ObjectProperty offset 0x0 element 8
  ItemId StructProperty offset 0x8 element 8
  SpawnTransform StructProperty offset 0x10 element 48

ServerRequestPlaceStructure: 13/13 properties
  StructureIndex IntProperty offset 0x0 element 4
  BuildLocation StructProperty offset 0x4 element 12
  BuildRotation StructProperty offset 0x10 element 12
  PlayerViewRotation StructProperty offset 0x1c element 12
  AttachToPawn ObjectProperty offset 0x28 element 8
  DinoCharacter ObjectProperty offset 0x30 element 8
  ParentStructure ObjectProperty offset 0x38 element 8
  BoneName NameProperty offset 0x40 element 8

ServerRequestTribeLog: 0/0 properties
```

## Result

Confirmed as `candidate-only`: the offline core has enough reflected metadata to plan a
general player/controller module roadmap across the full modding surface. The strongest next targets are:

1. Inventory item-use events, because their reflected property chains are small and
   reusable.
2. Dino stat request/response metadata, because it gives a compact object-param example.
3. Structure placement metadata, because it exercises structs, names, object params, and
   larger parameter buffers.
4. Tribe log requests as a low-parameter control observation.

No candidate is SDK-ready and no runtime invocation is implied.

## Risks

- Evidence is scoped to one ARK Linux binary hash and one existing core.
- Names and parameter chains prove metadata shape, not safe call semantics.
- Admin and transfer functions are high-risk surfaces and should stay documentation-only
  until permission, ownership, and abuse controls exist.
- Large `ParmsSize` candidates need struct decoding and second-core validation before any
  runtime experiment.

## Next Steps

1. Add focused reports for `PrimalItem`, `PrimalDinoCharacter`, and `PrimalStructure`.
2. Promote one inventory candidate into an offline analyzer fixture for property-chain
   decoding.
3. Add a general module taxonomy document mapping candidate families to future public SDK
   areas, still behind ABI and ownership gates.
4. Use TheIsland or a dedicated debug instance only after an explicit runtime validation
   window; keep Ragnarok out of this line of work.
