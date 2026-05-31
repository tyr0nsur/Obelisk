# General UFunction Inventory

> Historical inventory note. Commands below may reference protected
> `/servidor/ark/obelisk/dumps` evidence packs from prior work. Treat them as provenance,
> not current promotion instructions. Current player-identity work uses the non-protected
> raw-layout/core-pack route in
> `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.

## Objective

Move Obelisk research from a single event family into a broad offline inventory of
reflected `UFunction` objects from the existing core/evidence pack.

## Method

Added `scripts/summarize_core_ufunction_inventory.py`, an offline-only summarizer that:

- reads `--core` or preferred `--evidence-pack`;
- enumerates objects whose class resolves to `Function`;
- resolves outer object names/classes through the same FName/GObjects path;
- reads basic `UFunction` metadata candidates (`FunctionFlags`, `NumParms`, `ParmsSize`);
- groups functions by outer, outer class, and broad name family.
- supports focused filters such as `--outer-contains`, `--name-contains`, `--family`,
  `--min-params`, and `--max-params` for module-specific follow-up reports.
- reports optional `--target-set` coverage for UFunction target sets from
  `scripts/reflection_target_sets.py`, including matched, missing, and unassigned
  functions. ScriptStruct-only target sets are rejected by the CLI.
- emits a dry-run `--plan-regeneration` report that joins target-set membership,
  inventory coverage, and the candidate-only snapshot manifest. The plan distinguishes
  manifest-present, manifest-missing, inventory-missing, and ambiguous inventory targets
  without writing snapshots or promoting evidence. Planned commands are artifact-specific:
  evidence-pack runs use `--evidence-pack-manifest`, while direct-core runs include
  explicit `--gobjects` and `--fname-root-slot` arguments. The planner rejects snapshot
  manifests unless they are `source=offline_core` and `status=candidate-only`.

It does not attach to a process, run a scanner, promote offsets, or expose SDK APIs.

Validation command:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z \
  --max-objects 30000 \
  --max-groups 12 \
  --json > /tmp/obelisk-ufunction-inventory.json

python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /path/to/offline/core-pack \
  --target-set minimal-second-source-intake \
  --target-set structure-observer-intake \
  --json > /tmp/obelisk-ufunction-target-coverage.json

python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /path/to/offline/core-pack \
  --target-set minimal-second-source-intake \
  --plan-regeneration \
  --snapshot-manifest tests/fixtures/ufunction_snapshots/manifest.json \
  --json > /tmp/obelisk-ufunction-regeneration-plan.json
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
- Regeneration plans are review artifacts only. They must not be treated as accepted
  layouts, public SDK readiness, or authorization to write snapshots.
- Do not manually remove the planned `--evidence-pack-manifest`, `--gobjects`, or
  `--fname-root-slot` arguments; those keep second-source generation from falling back to
  primary-core defaults. When `--evidence-pack <dir>` is used, planned commands should use
  the normalized `<dir>/manifest.json` path.
- Broad families such as `BP`, `Get`, and `Set` are prioritization aids only; they are not
  runtime filters.

## Next Steps

1. Add focused inventory reports for `ShooterPlayerController`, `PrimalItem`, and
   `PrimalDinoCharacter`.
2. Use `--target-set --plan-regeneration` to identify which named promotion targets exist
   in a new offline artifact and which manifest entries need review before regenerating
   snapshots.
3. Select one gameplay family for deeper offline property-chain validation before any
   runtime experiment.
4. Keep SDK surfaces blocked until object lifetime, parameter ownership, and ABI shape are
   designed.

Follow-up started with
`docs/research/2026-05-27-shooterplayercontroller-function-inventory.md`, which identifies
inventory, dino, structure, tribe, transfer, notification, and admin clusters under
`ShooterPlayerController`.

## Scalar-Only Future Candidates

These are prioritization notes only. They must not become release gates or public SDK
events unless they later pass distinct second-source evidence, copied-data ownership,
runtime observation if required, lifecycle cleanup, and ABI/SDK tests.

- `PrimalStructure.SetVariant`: fixture-backed candidate in `structure-observer-intake`
  with `VariantIndex`, `bForceSet`, and `ReturnValue`. Keep it P1 internal and
  observation-only after `minimal-second-source-intake`; the `Set*` name and `bForceSet`
  imply mutation risk.
- `PrimalItem.CanRepair`: inventory-only finding for a compact repair gate. It needs a
  real snapshot, property-chain review, and second-source evidence before any target-set
  inclusion. Keep it behind the existing inventory minimal targets.
- `PrimalDinoCharacter.BP_CanFly`: inventory-only bool-return Blueprint hook. It may help
  bool-return coverage later, but dino fixtures such as `AddPassenger` and
  `AllowCarryCharacter` remain better P1 candidates.

If a future target set is added for these, name it as non-promotional candidate intake and
keep it out of `scripts/check_release_readiness.sh` defaults.
