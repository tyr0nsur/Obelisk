# General UFunction Inventory

## Objective

Move Obelisk research beyond chat-specific functions by producing a broad offline inventory
of reflected `UFunction` objects from the existing core/evidence pack.

## Method

Added `scripts/summarize_core_ufunction_inventory.py`, an offline-only summarizer that:

- reads `--core` or preferred `--evidence-pack`;
- enumerates objects whose class resolves to `Function`;
- resolves outer object names/classes through the same FName/GObjects path;
- reads basic `UFunction` metadata candidates (`FunctionFlags`, `NumParms`, `ParmsSize`);
- groups functions by outer, outer class, and broad name family.
- supports focused filters such as `--outer-contains`, `--name-contains`, `--family`,
  `--min-params`, and `--max-params` for module-specific follow-up reports.

It does not attach to a process, run a scanner, promote offsets, or expose SDK APIs.

Validation command:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z \
  --max-objects 30000 \
  --max-groups 12 \
  --json > /tmp/obelisk-ufunction-inventory.json
```

## Result

The current core inventory found `5269` `Function` objects within the first `30000`
`GObjects` entries.

Top name families:

```text
BP:837
Get:749
On:357
Server:314
Set:306
Is:281
Client:244
Add:88
```

Top outers:

```text
ShooterPlayerController:435
PrimalDinoCharacter:420
PrimalCharacter:395
ShooterCheatManager:327
VictoryCore:321
Actor:223
MissionType:223
PrimalItem:194
```

## Interpretation

Chat remains a useful validated path, but the broader roadmap should now use this inventory
to pick reusable module families:

- `ShooterPlayerController`: player/session/admin/client-server interaction candidates.
- `PrimalCharacter` and `PrimalDinoCharacter`: character and dino gameplay candidates.
- `PrimalItem`: inventory/item behavior candidates.
- `ShooterCheatManager`: admin/command-like function candidates, but likely unsafe as a
  public gameplay API without strict filtering.

## Risks

- This inventory is binary-hash-scoped to the existing core.
- Function names and metadata are offline evidence, not proof of safe invocation.
- `FunctionFlags`, `NumParms`, and `ParmsSize` are candidate reads until repeated on a
  second isolated core or future binary.
- Broad families such as `BP`, `Get`, and `Set` are prioritization aids only; they are not
  runtime filters.

## Next Steps

1. Add focused inventory reports for `ShooterPlayerController`, `PrimalItem`, and
   `PrimalDinoCharacter`.
2. Select one non-chat family for deeper offline property-chain validation before any
   runtime experiment.
3. Keep SDK surfaces blocked until object lifetime, parameter ownership, and ABI shape are
   designed.

Follow-up started with
`docs/research/2026-05-27-shooterplayercontroller-function-inventory.md`, which identifies
inventory, dino, structure, tribe, transfer, notification, and admin clusters under
`ShooterPlayerController`.
