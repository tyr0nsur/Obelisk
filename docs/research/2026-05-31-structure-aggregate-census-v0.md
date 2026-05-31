# Structure Aggregate/Census v0 Planning

## Objective

Define the next safe Structure direction after `v0.1.0-rc.2`: an aggregate/census
surface that can give plugin authors useful read-only build-pressure signals without
promoting public `StructureEvents`, structure identity, lookup, mutation, return override,
or `ResourceHandle`.

This note is planning only. It records the contract that an internal implementation
candidate must satisfy before any public SDK design is proposed.

## Current Evidence

- Current target-set seed: `structure-aggregate-census-planning`.
- Classification: planning-only / guidance-only, not release readiness.
- Seed targets are the same six compact Structure targets already accepted for
  `structure-observer-intake` layout evidence:
  - `PrimalStructure.AllowStructureAccess`
  - `PrimalStructure.IsAllowedToDemolish`
  - `PrimalStructure.SetVariant`
  - `PrimalStructureItemContainer.AllowToggleActivation`
  - `PrimalStructureItemContainer.VerifyPinCode`
  - `PrimalStructureSeating.CanSeat`
- Layout-only second-source evidence for those six targets is recorded in
  `2026-05-29-structure-observer-intake-refresh.md`.
- Non-PIN copied scalar evidence is recorded in
  `2026-05-30-structure-nonpin-copied-scalar-policy-slice.md`.

The accepted layout evidence supports copied/redacted `GameplayPolicyEvent` backing and
internal review. It does not prove a census SDK, object identity, runtime traversal, or
structure authority.

## v0 Contract

The first useful census design should be an internal snapshot/query model, not a public
push-event stream. It should count only Obelisk-owned, copied/redacted facts:

- event kind counters for the six known target functions;
- accepted/rejected recognizer counters by target;
- copied scalar field-mask counters;
- boolean outcome counters where safe and non-sensitive;
- non-identifying buckets derived from copied scalar categories, if a later note proves
  they cannot identify a player, base, tribe, location, or structure.

The unit is "reflected event shape plus copied/redacted scalar facts", not "this UE
structure". A future public form, if promoted, should prefer caller-copied snapshot data
over object handles. A plugin may compare snapshots in its own process-local memory, but
Obelisk must not imply cross-event identity, persistence, cluster state, or lookup.

## Allowed Internal Inputs

For an internal implementation candidate, the following copied scalars are usable as
inputs after exact shape validation and canonical bool checks:

| Target | Copied fields |
| --- | --- |
| `AllowStructureAccess` | `ReturnValue` bool |
| `IsAllowedToDemolish` | `ReturnValue` bool |
| `SetVariant` | `VariantIndex` int32, `bForceSet` bool, `ReturnValue` bool |
| `AllowToggleActivation` | `ReturnValue` bool |
| `CanSeat` | `bForce` bool, `ReturnValue` bool |

`VerifyPinCode` may contribute only metadata-level recognition/rejection counts unless a
future privacy review proves a narrower safe aggregate. Do not count or expose
`VerifyPinCode.ReturnValue`; it can create a PIN oracle even without exposing `pinCode`.

All bool values must be canonical bytes `0` or `1`; values greater than `1` fail closed.
Object refs, strings, arrays, structs, raw params, and UE pointers stay redacted or absent.

## Field Mask Model

Use an internal recognition mask aligned with the current `StructureField` enum:

```text
bit0 ForPC
bit1 ForCharacter
bit2 PinCode
bit3 VariantIndex
bit4 BForceSet
bit5 BForce
bit6 ReturnValue
```

| Target | Recognition mask | Copied/counted mask | Redacted mask |
| --- | ---: | ---: | ---: |
| `AllowStructureAccess` | `0x41` | `0x40` | `0x01` |
| `IsAllowedToDemolish` | `0x41` | `0x40` | `0x01` |
| `SetVariant` | `0x58` | `0x58` | `0x00` |
| `AllowToggleActivation` | `0x41` | `0x40` | `0x01` |
| `VerifyPinCode` | `0x44` | `0x00` | `0x44` |
| `CanSeat` | `0x63` | `0x60` | `0x03` |

Allowed counters by window and target:

- `matched_total`;
- `original_called_total`;
- `original_blocked_total`;
- `rejected_total_by_reason`;
- `redacted_field_present_total[field]`;
- `copied_field_present_total[field]`;
- `bool_true_total[field]` and `bool_false_total[field]`;
- `int32_present_total[field]`;
- capped `int32_value_histogram[field]` only for `VariantIndex`.

The histogram must cap cardinality per window and must not become an identity or location
side channel.

## Abort Conditions

An internal census accumulator must clear output and skip budget consumption when any of
these conditions occur:

- Structure gate disabled, missing profile/window/marker, missing SHA, or unsupported SHA.
- Both log and dispatch/census limits are zero.
- `nameIndex` is outside the six exact targets.
- `function == nullptr`, unsupported layout, reader exception, or invalid memory read.
- Function name, outer, `NumParms`, `ParmsSize`, `ReturnValueOffset`, or property count
  drifts from the accepted target spec.
- Property name, offset, size, `ElementSize`, `ArrayDim`, class name, or class object index
  drifts from the accepted field spec.
- Parameter range is absent, out-of-bounds, or size mismatched for a copied field.
- Any copied bool byte is greater than `1`.
- The original `ProcessEvent` did not run.
- Runtime logs or output would include PINs, player identifiers, object addresses,
  inventory/location data, broad traces, or any other privacy-sensitive value.

## Explicit Non-Claims

This plan does not promote:

- public `StructureEvents`;
- public Structure SDK;
- structure handles or `ResourceHandle`;
- player, tribe, owner, base, or structure identity;
- FName/GObjects indices as identity;
- lookup, traversal, linked-structure graphs, or cross-event correlation;
- exact coordinates, radii, placement structs, snap groups, pin codes, or player text;
- placement denial, no-collision, destroy/repair/change APIs, mutation, or return override;
- runtime observation or live-server testing without a current live-ops brief.

`APrimalStructure.IsAllowedToBuild` and `PrimalStructure.IsAllowedToBuild` remain
second-wave build-policy seeds. They are outside this v0 census plan until an exact
sanitized snapshot, redaction policy, distinct second-source comparison, and separate
promotion review exist.

## Product Uses That Are Honest

If promoted later, v0 could support:

- process-local aggregate audit logs by event kind and field mask;
- dashboard-style "build pressure" counters without identities or locations;
- rough, non-identifying category/bucket summaries;
- plugin-local trend comparisons between snapshots;
- descriptor/catalog examples that show what census categories exist.

Uses that must wait for player identity, `ResourceHandle`, or mutation gates:

- counts by player, tribe, alliance, owner, or base;
- "top tribes" or ownership reports;
- selecting, following, resolving, or inspecting one structure;
- correlating multiple events as the same structure;
- linked structure graphs, exact location/radius queries, safe-zone enforcement,
  no-collision, placement denial, destroy/repair/mutate behavior, or return override.

## Promotion Path

1. Keep `structure-aggregate-census-planning` planning-only and release-gate rejected.
2. Add focused guardrails for public docs/API claims around Structure aggregate/census
   before public wording grows.
3. Build an internal aggregate accumulator only over copied/redacted Structure event
   views, not raw UE params.
4. Test abort conditions: PIN result, object refs, FName/GObjects-as-identity, raw params,
   addresses, exact timestamps, exact locations, and unknown fields must not enter output.
5. If runtime evidence becomes necessary, request a scoped live-ops brief with instance,
   gates, window, privacy bounds, evidence path, and rollback. Do not infer approval from
   this plan.
6. Only after internal lifecycle, privacy, ABI, installed SDK consumer tests, and
   second-source/static evidence pass should a public SDK proposal be written.

## Offline Commands

List guidance without reading snapshots:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --list-target-guidance \
  --target-set structure-aggregate-census-planning \
  --json
```

Check the existing release Structure layout lane with sanitized fixture inputs only:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --fail-on-readiness-gaps \
  --target-set structure-observer-intake \
  --json
```

This second command is expected to require a distinct `--candidate-root` for a real
second-source readiness check. Do not use `/servidor/ark` live roots, restarts, ptrace,
gcore, markers, or ReflectionScanner for this planning step.
