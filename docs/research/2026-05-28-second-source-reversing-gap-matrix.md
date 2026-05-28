# Second-Source Reversing Gap Matrix

## Objective

Convert the broad "get a second source" requirement into concrete acceptance gates for
`FName`/`GNames`, `GUObjectArray`, `UObject`, `UFunction`, and module fixtures. This note is
planning only. It does not authorize server restarts, marker changes, ptrace, `gcore`,
ReflectionScanner, native exec probes, or runtime observation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Current baseline for artifact-identity gates:
  `e6367bf Require independent snapshot evidence identity`
- Current ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Existing primary core source:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Existing `GUObjectArray` research-candidate: `0x595b7e0`
- Existing static FName root slot evidence: `0x5956f30` only in the primary core context;
  a later post-start runtime probe rejected that slot, so it must not be promoted.
- Live impact: none.

## Source Classes

| Source | Counts As | Does Not Count As |
| --- | --- | --- |
| Second isolated core from `arkserver-obelisk-debug` | Strong second runtime-state source if binary hash, instance id, markers, and posture are recorded. | Authorization to touch Ragnarok or promote offsets automatically. |
| Approved `arkserver2` / TheIsland core fallback | Second source only if explicitly approved for that window and rolled back to stable posture. | Scanner-safe by default. |
| Static xref/decompiler path from matching binary | Independent static path for a candidate field/root when it explains initialization, lookup, bounds, or destructor flow. | Proof of live table contents by itself. |
| ReflectionScanner isolated capture | Candidate ranking for `GNames`/`GObjects` when logs include strict clues and no reject markers. | Stable runtime offset without second capture or static path. |
| Existing fixture snapshots from one core | Regression fixtures and module triage. | Public SDK or runtime-stable evidence. |

## P0 Matrix

| Area | Current State | Second-Source Acceptance | Commands When Artifact Exists | Reject/Block |
| --- | --- | --- | --- | --- |
| `FName` / `GNames` | Primary core has useful FName clues; current live logs without scanner are inconclusive. | `None`, `ClientMessage`, and `ServerChat` resolve through the same bounded table/pool; analyzer has no reject markers; evidence includes binary SHA, Obelisk commit, copied log/core path, and either a second isolated capture or static xref path. | `python3 scripts/analyze_reflectionscanner_capture.py --json --binary <ShooterGameServer> --objdump-xrefs <objdump> <copied-log>`; for core packs, first scan or derive a per-artifact FName table/root, then pass it explicitly, for example `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --scan-fname-tables --fname-root-slot verified_fname_root_slot=<verified-slot> --fname-index None=0 --fname-index ClientMessage=4884 --fname-index ServerChat=9619 --fname-index SetActiveMissionDebugFlags=9622`. Core packs also emit `fname-static-xrefs.json`; only non-oversized xref windows are actionable. | Single-source table, clue swap, implausible counts, readable-printable-memory heuristic, runtime probe rejection ignored, reused primary-core-only FName root slot, empty or contaminated static xref windows. |
| `GUObjectArray` / `GObjects` | `0x595b7e0` is a binary-hash-scoped research-candidate. | Second core or static path shows chunk/root/count/serial behavior; at least two sampled objects round-trip through `InternalIndex`; class and outer checks are plausible through object-array membership. | `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --gobjects-candidate gobjects=0x595b7e0 --fname-root-slot verified_fname_root_slot=<verified-slot> --gobjects-sample-index 0 --gobjects-sample-index 1 --gobjects-sample-index 25447`. | High object-shape score alone, no `InternalIndex` backref, class/outer merely readable, broad memory scans, default primary FName root mixed into second-source sampling. |
| `UObject` base | RuntimeReflection has a candidate layout; fixtures validate synthetic and primary-core shapes. | Second source confirms vtable, flags, internal index, class, name, outer; object pointer is reachable from `GObjects[InternalIndex]`. | `python3 scripts/enumerate_core_uobjects.py --core <core> --gobjects <verified-gobjects> --fname-root-slot <verified-fname-root-slot> --max-objects 30000 --class-contains Function --json`. | Class pointer not in `GObjects`, outer chain loops, FName only numeric, bad vtable/range, reused primary-core-only FName root slot. |
| `UFunction` / `UProperty` | Primary core supports property-chain snapshots and internal recognizers. | Second core or static path repeats target identity, outer/class membership, `NumParms`, `ParmsSize`, `ReturnValueOffset`, property names/classes/offsets/sizes. | `python3 scripts/inspect_core_ufunctions.py --core <core> --gobjects <verified-gobjects> --fname-root-slot <verified-fname-root-slot> --name-exact <target> --outer-exact <outer> --max-object-scan 30000 --snapshot-json`. | String proximity only, executable-tail heuristic only, chain loops, property count mismatch, offsets outside `ParmsSize`, reused primary-core-only FName root slot. |

After a second-source snapshot set exists, compare sanitized layouts offline before
updating any module status:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots/<sha-prefix>/<module> \
  --candidate-root <second-source-ufunction-snapshots>/<sha-prefix>/<module> \
  --target <Outer.Name> \
  --json
```

Use `--json` for evidence packs. The comparator ignores commit, metadata, and unstable
FName/GObjects indices by default; it returns `accepted`, `rejected`, or `inconclusive` per
target. Use `--strict-identity-indices` only when intentionally comparing same-binary
identity evidence, not for cross-source layout promotion.
Second-source comparison now requires sanitized artifact identity in snapshot evidence.
Each side should record `artifact_kind`, `artifact_sha256`, `capture_id`, and
`evidence_pack_id`; missing identity, fully matching identity, or shared
`artifact_sha256`/`capture_id`/`evidence_pack_id` is `inconclusive`, even when layouts
match. This prevents self-comparison or partial reuse of the same capture/evidence pack
from looking like independent acceptance. Readiness JSON includes per-module
`target_details` entries with each target key, source path, comparability, block reasons,
and second-source status, plus a top-level `promotion_gate` summary with `ready` and
blocker counts. Use those details in evidence packs instead of manually reconstructing
which target is still missing, inconclusive, or layout-rejected.
If a target-set entry is missing from the base fixture root, its second-source status is
`not_applicable`; fix base coverage before interpreting second-source readiness for that
target.

Before a second-source snapshot set exists, use the readiness report to keep module
coverage and missing second-source evidence explicit:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --readiness-report
```

For `sdk.transfers` ScriptStruct fixtures, the committed snapshots now preserve
target/property object indices and FName identity fields. Regeneration remains an offline
core workflow; use `regenerate_scriptstruct_snapshots.py --check-layout` only with full
artifact identity and an explicit per-artifact `--fname-root-slot` as a
semantic/layout-only check that ignores evidence commit churn and unstable
capture-specific indices, then use `compare_reflection_snapshots.py` for cross-source
semantic layout comparison. Use strict identity comparison only when intentionally
checking same-binary identity evidence.

For UFunction fixtures, `regenerate_ufunction_snapshots.py --check-layout` provides the
same same-target semantic regeneration gate and also requires full artifact identity plus
an explicit per-artifact `--fname-root-slot`: it ignores evidence commit churn and
unstable identity indices while still checking `NumParms`, `ParmsSize`, function flags,
return offset, and property-chain layout. This prevents second-source evidence packs from
silently reusing the primary-core FName root default; derive or scan the FName root for the
artifact first.
Likewise, `build_core_dump_evidence_pack.py --gobjects-sample-index` now requires an
explicit `--fname-root-slot` for the sampled artifact and resolves sampled names only
through explicit roots in that mode. Use `--scan-fname-tables` or a static derivation
first, then pass the verified root to GObjects/UObject sampling.
Core evidence pack manifests now expose a structured `promotion_gate` with `ready=false`
and blocker reasons. A generated static xref artifact removes the static-xref blocker only
when at least one non-oversized anchor window exists; empty or contaminated xref groups
remain non-actionable.

## P1 Module Fixture Matrix

| Module | Current Best Use | Second-Source Promotion Gate | Still Blocked |
| --- | --- | --- | --- |
| `sdk.inventory` | Internal marker-gated metadata observer for `CanUse` and `AllowRemoteAddToInventory`. | Second-source UFunction shape for both targets plus one approved debug observation with budget and no value logging. | Item ids, inventory contents, cooldown bypass policy, callbacks, return overrides. |
| `sdk.structures` | Internal marker-gated metadata observer for compact scalar structure functions. | Second-source shape for current six targets plus approved debug observation; pincode remains sensitive. | Placement/build/snapping mutation, raw pincode values, player identity. |
| `sdk.dinos` | Offline fixtures for compact passenger/carry shapes. | Second-source shape for `AddPassenger` and `AllowCarryCharacter`; no arrays or actor identity exposure. | Taming mutation, attacks, controller stats, generic actor refs. |
| `sdk.buffs` | Offline internal recognizer plus 6 real `PrimalBuff` fixtures cover compact bool returns, object/class metadata, and a zero-param target. | Second-source compact bool/scalar targets first: `AllowPostProcessEffect`, `BPBuffPreventUploading`, and `BP_OnBuffLifetimeUpdated`; keep ranges internal and metadata-only. | Runtime hooks, callbacks, return override, mutation of add/prevent/upload policy, raw `UObject*`/`UClass*`, mission/grapple/companion semantics, arrays/strings. |
| `sdk.tribes` | Offline permission/membership fixtures. | Second-source scalar permission targets with identity redaction policy. | Tribe logs, online arrays, player/tribe identity callbacks. |
| `sdk.missions` | Offline lifecycle fixtures. | Second-source compact lifecycle targets with arrays metadata-only. | Usable-item arrays, mission payload dispatch. |
| `sdk.transfers` | UFunction fixtures plus two candidate ScriptStruct fixtures. | Second-source layout-only comparison for `ARKTributeDino` and `ArkTributePlayerData`. | `ItemNetInfo`, upload/download runtime dispatch, nested arrays/strings. |

## Minimal Second-Source Intake

Use this first intake before expanding more gameplay surfaces. It is deliberately small:
two inventory functions and two structure functions that already have primary snapshots and
internal observer plans, without arrays, strings, raw identity exposure, callbacks, return
overrides, or gameplay mutation.

| Module | First Targets | Why These First |
| --- | --- | --- |
| `sdk.inventory` | `PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory` | Compact item-policy shapes with existing internal observer gates; useful for validating bool/scalar layout comparison before item contents or inventory arrays. |
| `sdk.structures` | `PrimalStructure.AllowStructureAccess`, `PrimalStructure.IsAllowedToDemolish` | Compact structure access/demolish shapes with existing marker-gated observation policy; avoids pincode and placement/build mutation surfaces. |

Current primary readiness, before any second artifact exists:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set minimal-second-source-intake \
  --fail-on-readiness-gaps
```

Expected current result:

```text
readiness targets=4 comparable=4 blocked=0 second_source_status=missing_candidate_root
ufunction:sdk_inventory targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
ufunction:sdk_structures targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
```

This is the promotion-gate form and should exit non-zero until the second source exists.
Omit `--fail-on-readiness-gaps` only when generating an informational gap report that must
not block the current core-first release gate.

When a second sanitized snapshot root exists, compare only this intake first:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <second-source-ufunction-snapshots> \
  --target-set minimal-second-source-intake \
  --json
```

Promotion requires all four targets to be `accepted` by
`compare_reflection_snapshots.py`, with non-empty sanitized artifact identity on both
roots: `artifact_kind`, `artifact_sha256`, `capture_id`, and `evidence_pack_id`. The
second source must use distinct `artifact_sha256`, `capture_id`, and `evidence_pack_id`;
missing or shared identity remains `inconclusive`, even when layouts match. Evidence must
also record binary SHA, Obelisk commit, artifact path, commands, reject conditions checked,
and an explicit statement that no live server was touched unless the artifact came from an
operator-approved debug capture. Even after layout acceptance, runtime observation remains
separate and must use a named debug instance, marker/env/SHA/budget gates, no value logging,
and no public SDK callbacks.

## Transfer ScriptStruct Intake

Use this focused intake for the first transfer struct second-source comparison. It stays
offline and layout-only; it does not authorize upload/download runtime dispatch or nested
payload decoding.

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --readiness-report \
  --target-set transfer-scriptstruct \
  --fail-on-readiness-gaps
```

Expected current result:

```text
readiness targets=2 comparable=2 blocked=0 second_source_status=missing_candidate_root
scriptstruct:sdk_transfers targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
```

The command above is the promotion-gate form and should exit non-zero until the second
source exists. Omit `--fail-on-readiness-gaps` only when generating an informational gap
report that must not block the current core-first release gate.

When a second sanitized ScriptStruct root exists:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --candidate-root <second-source-scriptstruct-snapshots> \
  --target-set transfer-scriptstruct \
  --json
```

## Evidence Pack Checklist

Every second-source note or evidence pack should record:

- target instance and map;
- ARK binary path and SHA256;
- Obelisk commit;
- sanitized artifact identity fields: `artifact_kind`, `artifact_sha256`, `capture_id`,
  and `evidence_pack_id`;
- core/log path and SHA256 where applicable;
- active Obelisk env and markers;
- command lines used;
- candidate addresses and why each is accepted, rejected, or inconclusive;
- static xref artifact path if used;
- post-run stable posture result for any approved debug capture;
- explicit statement that Ragnarok was not touched.

## Priority Order

1. Obtain or prepare an approved second isolated core path for `FName`/`GObjects`.
2. Re-run object enumeration and `UFunction` property-chain inspection on that second core.
3. Compare existing module snapshots layout-only against the second source with
   `scripts/compare_reflection_snapshots.py` when available.
4. Only then schedule short, marker-gated observation for inventory or structures on a
   named approved debug target. Prefer a dedicated `arkserver-obelisk-debug` instance; if
   using the current cluster, use `arkserver2` / TheIsland only inside an explicit
   operator-approved window and shut it down afterward. Keep `arkserver` / Ragnarok
   untouched while users are active.
5. Define SDK promotion policy after copied-data ownership and ABI lifecycle are proven.

## Current Result

No second source is currently available in-repo. Existing recognizers and observers remain
internal and experimental. The next productive work is either an approved isolated artifact
capture or tooling that makes the second-source comparison deterministic once that artifact
exists.
