# Structure Non-PIN Copied-Scalar Policy Slice

## Objective

Preserve a focused offline Structure policy slice for non-PIN targets. This is a
consume-mode artifact shape for copied scalar review only; it does not promote public
`StructureEvents`, runtime hook wiring, identity, lookup, mutation, or return override.

## Target Set

```text
structure-nonpin-copied-scalar-policy-slice
```

Targets:

```text
PrimalStructure.SetVariant
PrimalStructureItemContainer.AllowToggleActivation
PrimalStructureSeating.CanSeat
```

`PrimalStructureItemContainer.VerifyPinCode` is intentionally absent from the target set
and generated payload. It may appear only in boundary text because copied pin-validation
evidence would create a pin oracle.

## Copied Fields

```text
PrimalStructure.SetVariant.VariantIndex
PrimalStructure.SetVariant.bForceSet
PrimalStructure.SetVariant.ReturnValue
PrimalStructureItemContainer.AllowToggleActivation.ReturnValue
PrimalStructureSeating.CanSeat.bForce
PrimalStructureSeating.CanSeat.ReturnValue
```

Object references remain redacted:

```text
PrimalStructureItemContainer.AllowToggleActivation.ForPC
PrimalStructureSeating.CanSeat.ForPC
PrimalStructureSeating.CanSeat.forCharacter
```

## Result

The builder emits `obelisk.structure-nonpin-copied-scalar-policy-slice.v1` from committed
UFunction fixtures. The offline artifact gate accepts the slice in consume mode and blocks
promotion with `promote_mode_structure_nonpin_copied_scalar_policy_slice_evidence_only`.

Generated artifact pack:

```text
/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/
```

Files:

```text
artifact-pack.manifest.json
SHA256SUMS
structure-nonpin-copied-scalar-policy-slice.json
structure-nonpin-copied-scalar-policy-slice.consume-gate.json
structure-nonpin-copied-scalar-policy-slice.promote-gate.json
```

Gate result:

```text
consume: accepted mode=consume blockers=0
promote: blocked mode=promote blockers=2
```

Validation performed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_redacted_ufunction_signatures scripts.test_validate_offline_artifact_gate scripts.test_reconcile_gobjects_samples
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_compare_reflection_snapshots
```

## Boundary

This slice is internal evidence only. It does not authorize public SDK callbacks, public
metadata helpers, `ResourceHandle`, player/controller/character identity, structure
identity, object lookup, mutation, return override, dispatcher wiring, hook wiring, runtime
observation, or server-side probing.

## Internal Runtime Follow-Up

The structure reflection runtime now has an explicit internal non-PIN copied-scalar
boundary for this target set. The general structure recognizer still accepts the existing
six structure targets, including historical `VerifyPinCode`, `AllowStructureAccess`, and
`IsAllowedToDemolish` paths. New non-PIN helpers accept only:

```text
SetVariant
AllowToggleActivation
CanSeat
```

Use the non-PIN helpers when a path must reject PIN/access/demolish targets before
building a copied event or reserving dispatch budget. This is still internal plumbing
only: it does not promote public `StructureEvents`, add ABI, enable runtime observation,
or authorize server tests.
