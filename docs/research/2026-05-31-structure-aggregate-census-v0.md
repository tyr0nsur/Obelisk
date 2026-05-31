# Structure Aggregate/Census v0 Refinement

## Scope

This note refines the internal v0 aggregate/census design for Structure observations.
It is planning-only and records a copied/redacted aggregate contract. It does not promote
public `StructureEvents`, a Structure SDK, structure identity, lookup, mutation, return
override, or `ResourceHandle`.

The safe unit is "validated reflected event shape plus copied/redacted scalar facts".
It is not "this UE structure", "this player", "this tribe", "this base", or any stable
cross-event object.

## Event Sources

v0 may aggregate only the six compact Structure targets already accepted for
`structure-observer-intake` layout evidence and only after the original `ProcessEvent`
call reports that the original path ran:

| Target | v0 source status |
| --- | --- |
| `PrimalStructure.AllowStructureAccess` | Count recognition plus copied `ReturnValue` bool. |
| `PrimalStructure.IsAllowedToDemolish` | Count recognition plus copied `ReturnValue` bool. |
| `PrimalStructure.SetVariant` | Count recognition plus copied `VariantIndex` int32, `bForceSet` bool, and `ReturnValue` bool. |
| `PrimalStructureItemContainer.AllowToggleActivation` | Count recognition plus copied `ReturnValue` bool. |
| `PrimalStructureItemContainer.VerifyPinCode` | Count metadata-level recognition/rejection only. No result or PIN-derived aggregate. |
| `PrimalStructureSeating.CanSeat` | Count recognition plus copied `bForce` bool and `ReturnValue` bool. |

Accepted layout evidence for these targets is recorded in
`2026-05-29-structure-observer-intake-refresh.md`. Non-PIN copied scalar policy evidence
is recorded in `2026-05-30-structure-nonpin-copied-scalar-policy-slice.md`.

v0 inputs are copied scalar event views only. Raw UE params, object refs, strings,
arrays, structs, addresses, FName/GObjects indices, and caller/callee pointers are not
event sources.

## Privacy Exclusions

The aggregate must exclude values that can identify or help resolve a player, base,
tribe, owner, location, inventory, structure, or PIN state. Required exclusions:

- `pinCode`, `VerifyPinCode.ReturnValue`, and any PIN-success/failure aggregate;
- player/controller/character references and identifiers;
- tribe, alliance, owner, base, team, or structure identity;
- object addresses, UE pointers, raw params, FName/GObjects identity, and handle-like
  values;
- exact coordinates, radii, placement structs, snap groups, inventory/container details,
  item identifiers, strings, and free text;
- exact per-event timestamps or sequence data that enables cross-event correlation.

`VariantIndex` may be aggregated only through a capped per-window histogram. The cap must
keep the field from becoming an identity, location, or rare-configuration side channel.

## Lifecycle Gates

The census accumulator remains internal and default-off. It may produce an aggregate
window only when all lifecycle gates pass:

- Structure recognition gate enabled.
- Explicit profile/window/marker present.
- Binary SHA present and supported for the accepted target specs.
- Runtime budget available for the aggregate path.
- Exact target prefilter matched before any parameter read or budget reservation.
- Original `ProcessEvent` path completed before copied return data is counted.
- Output window contains only approved counters and capped histograms.

When a lifecycle gate fails, the accumulator must clear pending output and skip budget
consumption. A disabled gate, missing profile/window/marker, missing SHA, unsupported
SHA, zero budget, or non-target `nameIndex` must not read metadata or params.

## Validation Gates

Each counted event must pass the same strict reflected-shape gates used for copied
Structure event views:

- exact function name, outer, `NumParms`, `ParmsSize`, property count, and accepted
  return offset;
- exact property name, offset, size, `ElementSize`, `ArrayDim`, class name, and schema
  class-object check for every copied field;
- copied field ranges present, in bounds, and size-matched;
- copied bool bytes canonical: only `0` and `1` are accepted;
- rejection paths clear copied output;
- redacted fields may influence only redaction/recognition counters, never copied values;
- unknown, drifted, out-of-bounds, or exception-backed reads fail closed.

Allowed counters by target/window:

- `matched_total`;
- `original_called_total`;
- `original_blocked_total`;
- `rejected_total_by_reason`;
- `redacted_field_present_total[field]`;
- `copied_field_present_total[field]`;
- `bool_true_total[field]` and `bool_false_total[field]`;
- `int32_present_total[field]`;
- capped `int32_value_histogram[VariantIndex]`.

No aggregate output may include raw values for redacted fields, object identity, player
identity, exact location, exact timestamp, or any field outside the approved copied scalar
set.

## Blocked

The following remain blocked for v0:

- public `StructureEvents`, public Structure SDK, or public aggregate/census SDK claims;
- structure handles, `ResourceHandle`, lookup, traversal, linked-structure graphs, or
  cross-event correlation;
- player, tribe, owner, base, location, or structure-scoped counts;
- PIN validation outcomes, PIN-derived aggregates, and `pinCode` exposure;
- object refs, strings, arrays, structs, raw params, UE pointers, addresses, FName/GObjects
  identity, and exact timestamps in output;
- placement denial, no-collision, destroy/repair/change APIs, mutation, return override,
  or manually calling original `ProcessEvent`;
- runtime observation, live-server testing, restarts, markers, ptrace, gcore, broad
  tracing, or `/servidor/ark` access without a separate current live-ops brief.

`APrimalStructure.IsAllowedToBuild` and `PrimalStructure.IsAllowedToBuild` remain
second-wave build-policy seeds. They are outside v0 until an exact sanitized snapshot,
redaction policy, distinct second-source comparison, and separate promotion review exist.

## Offline Check

The planning target set can be listed without reading snapshots or touching servers:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --list-target-guidance \
  --target-set structure-aggregate-census-planning \
  --json
```

Current supporting policy-slice artifacts are usable only as internal evidence. They must
continue to pass consume mode and block promote mode before any implementation work cites
them:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.json \
  --mode consume \
  --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.json \
  --mode promote \
  --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.json \
  --mode consume \
  --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.json \
  --mode promote \
  --json
```

Observed on 2026-05-31: both consume gates returned `status=accepted`; both promote gates
returned `status=blocked` with evidence-only/non-claim blockers. That is the intended
state for v0 planning: useful enough to design internal copied counters, not promotable
as a public Structure SDK or runtime claim.

## Materialized Aggregate Policy Slice

The aggregate/census slice itself is now materialized as an offline artifact pack:

- root: `/home/flowcommunity-ark/obelisk-artifacts/structure-aggregate-census-policy-slice-20260531T034715Z`
- report: `structure-aggregate-census-policy-slice.json`
- report sha256: `15bc87854cc85e1bd4ed9a8658a3b1d83b41a4b1f8f52f967d17ea25421180dd`
- artifact manifest sha256: `876d38ddfdbd9944734741bad2c415c733afac062d91ab533869849927ff5906`
- `SHA256SUMS` sha256: `df18283db97eaa4c2620460d2a28603f44b9ee3eebd927d6792c83505e6f2251`

Validation on 2026-05-31:

- `normalize_artifact_pack.py --check`: `status=ok`
- `validate_offline_artifact_gate.py --mode consume`: `status=accepted`
- `validate_offline_artifact_gate.py --mode promote`: `status=blocked`

The report preserves `policy_status=evidence-only`, `consume_only=true`,
`promotion_ready=false`, 6 input targets, 8 copied fields, 5 redacted fields, and 2
explicitly excluded fields. Promote mode blocks with
`promote_mode_structure_aggregate_census_policy_slice_consume_only` and
`promote_mode_manifest_has_non_claims`, which is the intended state.

Do not use live roots, restarts, ptrace, gcore, markers, `/servidor/ark`, or
`ReflectionScanner` for this planning note.

## Internal Accumulator Checkpoint

The first internal C++ accumulator now exists as `core/StructureAggregateCensus.*`, with
fixture-backed coverage in `tests/core/StructureAggregateCensusTests.cpp`. It is compiled
into `libobelisk.so` but is not wired to a hook, plugin API, public descriptor, installed
SDK header, or runtime marker.

The accumulator consumes only copied `StructureEventView` scalar data, remains default-off
through explicit options, enforces a bounded window after the exact non-PIN copied-scalar
prefilter, excludes `VerifyPinCode`, and caps the `VariantIndex` histogram. Rejected
sensitive/non-structure and unexpected-shape events do not consume the accepted-event
window; post-window overflow is counted as a bounded rejection signal. Its snapshot
contains only counters and histogram buckets; it does not carry function indices, outer
indices, timestamps, coordinates, player/tribe/base identity, object handles, raw params,
mutation decisions, or return-override authority.

Validated locally:

```bash
cmake --build build --target obelisk structure_aggregate_census_tests -j"$(nproc)"
./build/structure_aggregate_census_tests
ctest --test-dir build -R 'StructureAggregateCensusTests|StructureEventDispatcherTests|ProcessEventMissionReflectionTests|MissionCopiedBoolEventDispatcherTests' --output-on-failure
```

This remains an internal planning/product-value bridge only. The next promotion step would
need separate lifecycle gates, runtime approval, no-read/no-budget hook tests, privacy
review, and SDK consumer design before any public Structure aggregate/census surface is
claimed.
