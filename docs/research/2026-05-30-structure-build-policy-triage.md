# Structure Build Policy Triage

Date: 2026-05-30

## Objective

Assess whether `APrimalStructure.IsAllowedToBuild` should become the next Obelisk
structure reflection target after the accepted `structure-observer-intake` lane.

## Inputs

- Local compatibility dictionary: `/home/flowcommunity-ark/NextGenPlugins`
- Existing structure inventory:
  `docs/research/2026-05-27-primalstructure-function-inventory.md`
- Existing committed fixtures: `tests/fixtures/ufunction_snapshots`
- Existing target-set registry: `scripts/reflection_target_sets.py`

No server process, runtime observation, ReflectionScanner, ptrace/gcore, marker/env
change, Discord update, or `/servidor/ark` write was used for this triage.

## Demand Signal

The local ArkApi plugin-source clone shows repeated build-policy demand for
`APrimalStructure.IsAllowedToBuild` in structure-limit, safe-zone, and no-collision style
plugins. Use this only as a names and behavior dictionary. Do not copy ArkApi offsets,
layouts, wrappers, MSVC ABI, direct UE pointer access, or implementation.

Dictionary seed names to resolve through Obelisk reflection only:

- `APrimalStructure.IsAllowedToBuild`
- `PC`
- `AtLocation`
- `AtRotation`
- `OutPlacementData`
- `bDontAdjustForMaxRange`
- `PlayerViewRotation`
- `bFinalPlacement`
- `ReturnValue`

The high-level behavior categories are:

- structure limit enforcement;
- safe-zone build restriction;
- no-collision/admin allowlist behavior;
- player/location/rotation/build-placement context;
- possible return-value or placement-result policy.

## Current Obelisk State

`IsAllowedToBuild` is not part of committed structure fixtures or named target sets.
Current committed structure snapshot targets are:

- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`
- `PrimalStructure.SetVariant`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureSeating.CanSeat`

The existing structure notes deliberately classify placement/build functions as deferred:
they are larger, struct-heavy, authority-sensitive, and mutation/return-policy prone.

Current fixture gap check:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild \
  --json
```

Result: `missing_base_snapshot`, `layout_ready=false`, `promotion_ready=false`.

The explicit ArkApi-style spelling also stays missing:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild \
  --json
```

Result: `missing_base_snapshot`, `layout_ready=false`, `promotion_ready=false`.

Accepted structure work today remains narrower:

- `structure-observer-intake`: six target layout evidence root;
- `structure-return-only-policy-slice`: copied `ReturnValue` only for access/demolish;
- `structure-nonpin-copied-scalar-policy-slice`: copied scalars for non-PIN internal
  review.

Those lanes do not promote public `StructureEvents`, build-policy SDK, identity, lookup,
mutation, return override, or runtime hook authorization.

## Decision

`APrimalStructure.IsAllowedToBuild` is a valid post-RC research target, but it is not ready
for target-set promotion. Treat it as a second-wave structure build-policy candidate until
offline reflection proves its exact UFunction name, owner, `ParmsSize`, property chain,
struct fields, return semantics, and redaction policy.

Do not add it to `structure-observer-intake`, `minimal-second-source-intake`, release
gates, public descriptors, ABI enums, SDK examples, or runtime dispatchers from this
triage alone.

## Minimum Next Offline Step

When a scoped offline core/snapshot task is approved, first generate a sanitized
candidate snapshot for the exact target only. Because this target is not in the current
fixture manifest, use the ad hoc inspection path before adding any target set:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core <offline-core> \
  --outer-exact PrimalStructure \
  --name-exact IsAllowedToBuild \
  --inspection-mode ufunction \
  --snapshot-json \
  --evidence-ark-sha256 <ark-binary-sha256> \
  --evidence-artifact-sha256 <offline-core-or-pack-sha256> \
  --evidence-artifact-kind offline_core \
  --evidence-capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-pack-id> \
  --evidence-obelisk-commit <commit>
```

Then review and redact the candidate snapshot. Add a named target set only after a fixture
exists and the payload/redaction policy is explicit. Compare only when a committed/base
snapshot and a distinct second source both exist.

## Promotion Blockers

- No committed sanitized snapshot currently exists for `PrimalStructure.IsAllowedToBuild`.
- No second-source comparison currently exists for the target.
- Placement output structs and location/rotation context need redaction and ownership
  policy before any copied payload can be considered.
- Player/controller identity, structure identity, location data, object refs, and
  placement structs must remain redacted until separate privacy and ABI policy exists.
- Return override/build denial is a separate mutation/authority feature and remains
  blocked.
- Return-code semantics for Linux ARK are not accepted. Do not infer allow/deny constants
  from ArkApi code.
- Multi-plugin arbitration is undefined. A future enforcing API would need deterministic
  deny-only semantics, exception/timeout behavior, and lifecycle cleanup before public use.

## Staging Ladder

1. Candidate snapshot: exact `PrimalStructure.IsAllowedToBuild` metadata only.
2. Redacted signature: copied scalar candidates only, with object refs, placement structs,
   and location/rotation context redacted unless separately promoted.
3. Second-source layout: distinct sanitized artifact comparison, consume-only and
   promote-blocked.
4. Internal observation: post-original copied observation only, no blocking, no mutation,
   no return override.
5. Shadow policy: internal would-deny calculation without changing gameplay.
6. Public policy, later: append-only C/POD API with owner-token registration, ABI tests,
   installed SDK consumer tests, privacy policy, lifecycle cleanup, and deny-only
   arbitration. Plugins may not force-allow, mutate placement data, call UE, or expose raw
   object identity.

## Non-Claims

This triage does not promote a public Structure SDK, build-policy API, `StructureEvents`,
runtime hook, callback, identity/lookup surface, mutation, return override, safe-zone API,
no-collision compatibility, or ArkApi port.
