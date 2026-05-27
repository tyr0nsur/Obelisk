# Structure Access Policy Fixtures

## Objective

Promote the next `sdk.structures` slice from inventory-only to fixture-backed offline
coverage, focused on access, demolish, pincode, variant, and seating policy surfaces.

## Environment

- Evidence source: synthetic analyzer fixtures derived from
  `docs/research/2026-05-27-primalstructure-function-inventory.md`.
- ARK binary SHA256 for the source inventory:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Obelisk commit before this note: `17e05ae Update fixture-backed module taxonomy`.
- Instance source: offline core/inventory evidence only.
- Live-server impact: none; no `/servidor/ark` markers, restarts, scanners, or runtime
  probes were used.

## Hypothesis

Structure policy functions with only object, int, byte, and bool params are the best next
gameplay fixtures because they cover real modding decisions without requiring placement
structs, strings, arrays, or live authority mutation.

## Method

Extended `scripts/test_inspect_core_ufunctions.py` with fixture objects and property
chains for:

```text
PrimalStructure.AllowStructureAccess
PrimalStructure.IsAllowedToDemolish
PrimalStructure.SetVariant
PrimalStructureItemContainer.VerifyPinCode
PrimalStructureSeating.CanSeat
```

The same round added `--snapshot-json` to `scripts/inspect_core_ufunctions.py`, producing
a sanitized fixture snapshot that preserves function/property shape and rejection reasons
while omitting core paths and absolute addresses.

## Evidence

Accepted fixture-backed chains:

```text
PrimalStructure.AllowStructureAccess
  ForPC ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1

PrimalStructure.IsAllowedToDemolish
  ForPC ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1

PrimalStructure.SetVariant
  VariantIndex IntProperty @0x0 size 4
  bForceSet BoolProperty @0x4 size 1
  ReturnValue BoolProperty @0x5 size 1

PrimalStructureItemContainer.VerifyPinCode
  pinCode IntProperty @0x0 size 4
  ReturnValue BoolProperty @0x4 size 1

PrimalStructureSeating.CanSeat
  ForPC ObjectProperty @0x0 size 8
  forCharacter ObjectProperty @0x8 size 8
  bForce BoolProperty @0x10 size 1
  ReturnValue BoolProperty @0x11 size 1
```

Validation:

```text
python3 scripts/test_inspect_core_ufunctions.py
Ran 26 tests: OK
```

## Result

Confirmed as `candidate-only`, now with synthetic fixture coverage. This improves
Obelisk's modding roadmap toward structure access policy and container/seating decisions,
but it does not create a public SDK API and does not authorize runtime observation.

The new snapshot output is suitable as the next bridge toward real-core fixture JSON
snapshots because it strips absolute addresses and local paths while keeping:

- target name and outer;
- object/class/outer membership status;
- `NumParms`, `ParmsSize`, function flags, return offset;
- ordered property names, classes, offsets, sizes, flags, and rejection reasons.

## Rejected Paths

- Structure placement/build functions remain deferred because they exercise larger
  struct-heavy params and carry higher gameplay-authority risk.
- `BPRename` and other `StrProperty` surfaces remain deferred behind `FString` ownership
  and runtime text gates.
- Runtime probes on Ragnarok remain out of scope; future runtime validation belongs on
  `arkserver2` or a dedicated isolated debug instance during an approved window.

## Risks

- The fixtures are synthetic and derived from one binary-hash-scoped offline inventory.
- Policy meaning is not accepted from metadata alone; actual allow/deny semantics require
  controlled runtime observation later.
- Pincode/admin-like surfaces need explicit API policy before public SDK exposure.

## Next Steps

1. Generate sanitized `--snapshot-json` outputs from real core evidence for the accepted
   compact chains.
2. Add a small committed snapshot fixture only after path/address redaction is reviewed.
3. Keep `sdk.structures` in `candidate-only` until a second evidence source and policy
   layer exist.
