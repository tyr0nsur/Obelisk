# Structure Return-Only Policy Slice

## Objective

Preserve the first focused internal Structure policy slice after the broader
`structure-observer-intake` evidence. This is a consume-mode artifact for copied scalar
review only; it does not promote a public Structure SDK or runtime hook.

## Artifact

```text
/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/
```

Files:

```text
structure-return-only-policy-slice.json
structure-return-only-policy-slice.consume-gate.json
structure-return-only-policy-slice.promote-gate.json
artifact-pack.manifest.json
SHA256SUMS
```

Pack hashes:

```text
artifact-pack.manifest.json sha256=8f97c679e8eb9bacaf9204218853fab9c7b0345b4431102d97ba985723718602
SHA256SUMS sha256=1e9a97b81b4bac124173275689258b1d201f3eb87023a85080954e15a7c7b099
```

## Result

Consume mode accepts the artifact. Promote mode blocks it as evidence-only.

Copied fields:

```text
PrimalStructure.AllowStructureAccess.ReturnValue
PrimalStructure.IsAllowedToDemolish.ReturnValue
```

Redacted fields:

```text
PrimalStructure.AllowStructureAccess.ForPC
PrimalStructure.IsAllowedToDemolish.ForPC
```

Explicitly deferred targets:

```text
PrimalStructureItemContainer.VerifyPinCode
PrimalStructureItemContainer.AllowToggleActivation
PrimalStructure.SetVariant
PrimalStructureSeating.CanSeat
```

## Boundary

This slice is internal layout/policy evidence only. It does not authorize public
`StructureEvents`, object/player identity, lookup, mutation, return override,
`ResourceHandle`, hook wiring, dispatcher wiring, or runtime observation. `VerifyPinCode`
stays excluded because even a copied return bool would expose a pin-validity oracle.
