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

The fixture-only `missing_base_snapshot` result is already conclusive for repo state.
Do not spend another pass rerunning target-set or fixture coverage checks to find this
lane. The next useful artifact is a new sanitized candidate snapshot generated from an
approved copied/offline core or complete evidence-pack manifest outside protected server
paths, with explicit FName root, GObjects, binary hash, and artifact identity.

When a scoped offline core/snapshot task is approved, first generate a sanitized
candidate snapshot for the exact target only. Because this target is not in the current
fixture manifest, use the ad hoc inspection path before adding any target set.

`scripts/inspect_core_ufunctions.py` currently takes an offline core via `--core`; do not
pass an evidence-pack manifest to `--core`. The inspector now rejects evidence-pack
manifests passed as `--core` before opening them as ELF cores. If the approved input is a
complete evidence-pack manifest instead of a copied core, use the snapshot regeneration
consumer for that manifest and keep the resulting target exact and ad hoc.

The command contract below was checked against the inspector CLI on 2026-05-30:
`--outer-exact`, `--name-exact`, `--inspection-mode ufunction`, `--snapshot-json`, and
the listed `--evidence-*` metadata flags are supported. The regression test
`test_cli_documented_structure_snapshot_flags_stay_supported` keeps the same flag family
covered with a synthetic offline fixture so future doc edits do not drift into a broken
command.

The snapshot path is now intentionally focused: `--snapshot-json` rejects substring
discovery filters, requires one direct target or both `--outer-exact` and `--name-exact`,
requires exactly one matched target, and only accepts `offline_core` /
`candidate-only` evidence labels. This prevents a future `IsAllowedToBuild` artifact from
accidentally becoming a broad discovery dump or a misleading promotion artifact.

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

## Offline Follow-up: Existing Artifact Check

Date: 2026-05-30

Scope: read-only repo and `/home/flowcommunity-ark/obelisk-artifacts` inspection only.
No server process, runtime observation, ptrace/gcore/scanner, code edit, commit, push,
tag, Discord update, or `/servidor/ark` read/write was used.

Commands run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild \
  --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild \
  --json

find /home/flowcommunity-ark/obelisk-artifacts -type f -size +100M -printf '%s %p\n' | sort -nr

strings -a /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/\
7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/\
ShooterGameServer | rg -i \
'allowedtobuild|placementdata|dontadjust|maxrange|finalplacement|player.*view.*rotation|atlocation|atrotation|primalstructure'
```

Results:

- Both exact target checks still report `missing_base_snapshot`,
  `layout_ready=false`, and `promotion_ready=false`.
- `scripts/reflection_target_sets.py` still has no
  `PrimalStructure.IsAllowedToBuild` or `APrimalStructure.IsAllowedToBuild` entry.
- The committed UFunction fixture manifest still has no build-policy target; current
  structure fixtures remain the six `structure-observer-intake` entries only.
- `/home/flowcommunity-ark/obelisk-artifacts` currently contains the offline
  `ShooterGameServer` binary and derived artifact packs, but no obvious raw core file
  suitable for `inspect_core_ufunctions.py`. The only file larger than 100 MB found in
  that tree was the static objdump text.
- Static strings from the offline binary show weak adjacent seeds such as
  `BPIsAllowedToBuild` and `BPIsAllowedToBuildEx`, but not an exact
  `IsAllowedToBuild` or `APrimalStructure.IsAllowedToBuild` UFunction snapshot. Treat
  these strings as discovery hints only; they do not prove owner, `ParmsSize`, property
  chain, return offset, placement struct layout, or copy/redaction policy.

Useful existing artifacts:

- Offline binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Static-global preflight:
  `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json`
  records the same binary SHA, the reviewed FName root slot candidate, and the
  `GUObjectArray` research-candidate. This is useful provenance for future offline
  core snapshot regeneration, but static evidence alone cannot enumerate this UFunction
  metadata.
- Minimal second-source structure evidence:
  `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/snapshot-comparison/readiness-report.json`
  accepts `PrimalStructure.AllowStructureAccess` and
  `PrimalStructure.IsAllowedToDemolish` layout-only evidence, but it does not cover
  build placement policy.

Minimum artifact still needed:

An approved copied/offline core or evidence-pack manifest outside protected server paths,
from the same binary hash or a properly documented second source, with usable FName root
slot and GObjects inputs. The minimum snapshot command remains the ad hoc
`inspect_core_ufunctions.py --snapshot-json` command above, targeting only
`--outer-exact PrimalStructure --name-exact IsAllowedToBuild`.

Tooling guardrail added during this triage follow-up:

- `scripts/inspect_core_ufunctions.py --snapshot-json` now fails closed unless the
  request is a single focused offline-core candidate snapshot with exact/direct target
  selection and complete candidate-only evidence metadata.
