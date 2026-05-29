# Second-Source Reversing Gap Matrix

## Objective

Convert the broad "get a second source" requirement into concrete acceptance gates for
`FName`/`GNames`, `GUObjectArray`, `UObject`, `UFunction`, and module fixtures. This note is
planning only. It does not authorize server restarts, marker changes, ptrace, `gcore`,
ReflectionScanner, native exec probes, or runtime observation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Repository baseline when artifact-identity gates were authored:
  `e6367bf Require independent snapshot evidence identity`
- Current ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Existing primary core source:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Existing primary core SHA256:
  `1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e`
- Available clean vanilla second-source candidate:
  `vanilla-gdb-arkserver2-TheIsland-20260529T012853Z`
- Vanilla candidate core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Vanilla candidate binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Vanilla candidate posture: `arkserver2` / TheIsland; pre-capture evidence records no
  Obelisk env, maps, or process evidence. Treat it as a clean independent runtime
  artifact for offline intake, not as accepted layout evidence by itself.
- Existing `GUObjectArray` research-candidate: `0x595b7e0`
- Existing static FName root slot evidence: `0x5956f30`. The clean vanilla second-source
  core resolved this slot to table `0x5a94660` and exact clues `None=0`,
  `ClientMessage=4884`, `ServerChat=9619`, and `SetActiveMissionDebugFlags=9622`. Treat
  it as binary-hash-scoped second-source evidence, not a universal offset.
- Clean vanilla `minimal-second-source-intake` result:
  `promotion_gate.ready=true`, `blockers=[]`, and `4/4` UFunction targets accepted for
  `sdk.inventory` and `sdk.structures` on the clean `arkserver2` / TheIsland artifact.
- Clean vanilla `structure-observer-intake` result:
  `promotion_gate.ready=true`, `blockers=[]`, and `6/6` `sdk.structures` UFunction
  targets accepted, including access, demolish, variant, activation, pincode verification,
  and seating checks. This supports a metadata-only structure observer surface; it does
  not authorize raw pincode values, player identity, mutation, or return overrides.
- Live impact: none.

## Source Classes

| Source | Counts As | Does Not Count As |
| --- | --- | --- |
| Second isolated core from `arkserver-obelisk-debug` | Strong second runtime-state source if binary hash, instance id, markers, and posture are recorded. | Authorization to touch Ragnarok or promote offsets automatically. |
| Approved `arkserver2` / TheIsland core fallback | Second source only if explicitly approved for that window and rolled back to stable posture. | Scanner-safe by default. |
| Clean vanilla `arkserver2` / TheIsland core `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb` | Independent second runtime artifact for FName/GObjects/UFunction offline intake because binary SHA, distinct core SHA, instance/map, and negative Obelisk posture evidence are recorded. It now accepts `minimal-second-source-intake` and `structure-observer-intake`. | Broad public SDK readiness, all-module promotion, raw pincode/player identity exposure, mutation/override APIs, or promoted `GObjects` global evidence beyond the reviewed target sets. |
| Static xref/decompiler path from matching binary | Independent static path for a candidate field/root when it explains initialization, lookup, bounds, or destructor flow. | Proof of live table contents by itself. |
| ReflectionScanner isolated capture | Candidate ranking for `GNames`/`GObjects` when logs include strict clues and no reject markers. | Stable runtime offset without second capture or static path. |
| Existing fixture snapshots from one core | Regression fixtures and module triage. | Public SDK or runtime-stable evidence. |
| Copied, renamed, repacked, or symlinked primary core `1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e` | Primary-source fixture provenance only, even if stored outside `/servidor/ark`. | Second source, independent capture, or `minimal-second-source-intake` evidence. |

## P0 Matrix

| Area | Current State | Second-Source Acceptance | Commands When Artifact Exists | Reject/Block |
| --- | --- | --- | --- | --- |
| `FName` / `GNames` | Static `0x5956f30` and clean vanilla core evidence agree for exact known clues. | `None`, `ClientMessage`, and `ServerChat` resolve through the same bounded table/pool; analyzer has no reject markers; evidence includes binary SHA, Obelisk commit or offline intake commit, copied log/core path, and either a second isolated capture or static xref path. | `python3 scripts/analyze_reflectionscanner_capture.py --json --binary <ShooterGameServer> --objdump-xrefs <objdump> <copied-log>`; for core packs, first scan or derive a per-artifact FName table/root with no default roots/candidates, for example `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --scan-fname-tables --no-default-candidates --no-default-fname-roots --no-default-fname-indices --fname-index None=0 --fname-index ClientMessage=4884 --fname-index ServerChat=9619 --fname-index SetActiveMissionDebugFlags=9622`. Core packs also emit `fname-static-xrefs.json`; only non-oversized xref windows are actionable. | Single-source table, clue swap, implausible counts, readable-printable-memory heuristic, runtime probe rejection ignored, reused primary-core-only FName root slot, empty or contaminated static xref windows. |
| `GUObjectArray` / `GObjects` | `0x595b7e0` is a binary-hash-scoped research-candidate. | Second core or static path shows chunk/root/count/serial behavior; at least two sampled objects round-trip through `InternalIndex`; class and outer checks are plausible through object-array membership. | After the per-artifact FName root is verified, sample with explicit roots/candidates only: `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --no-default-candidates --no-default-fname-roots --gobjects-candidate gobjects=0x595b7e0 --fname-root-slot verified_fname_root_slot=<verified-slot> --gobjects-sample-index 0 --gobjects-sample-index 1 --gobjects-sample-index 25447`. | High object-shape score alone, no `InternalIndex` backref, class/outer merely readable, broad memory scans, default primary FName root mixed into second-source sampling. |
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
blocker counts. Text reports also print `gate_mode=<mode>` and
`promotion_gate ready=<true|false>` with compact blocker counts before module details, so
informational reports cannot be confused with a promotion-ready gate. `promotion_gate.ready`
is allowed to become `true` only when the report is executed as
`gate_mode=second_source_promotion`; if every target compares cleanly in an informational
report, the gate is still blocked with `not_second_source_promotion_gate`. Use those
details in evidence packs instead of manually reconstructing which target is still
missing, inconclusive, or layout-rejected.
Promotion-gate runs also reject `--allow-ark-sha-mismatch`, reject direct or symlinked
snapshot roots under `/servidor/ark`, and require snapshots to record the expected
`generated_by` producer. Cross-binary or unknown-producer comparisons are diagnostic only,
not promotion evidence.
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

CI enforces base readiness for the committed promotion target sets with
`--fail-on-base-readiness-gaps`. That gate only proves the requested target sets have
non-empty comparable primary fixtures; it deliberately does not require candidate
second-source roots. Use the stricter `--fail-on-readiness-gaps` or
`scripts/check_release_readiness.sh --require-second-source-readiness` when reviewing an
actual promotion artifact.

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
artifact first. To reduce manual transcription, both UFunction and ScriptStruct
regenerators accept `--evidence-pack-manifest <pack>/manifest.json`; they require
`binary.sha256` to match the snapshot manifest `ark_binary_sha256`, require
`evidence_status.status=complete`, reject `gdb_core_failed=true`, read `core.sha256`,
derive a sanitized capture id from `core.path`, use the pack directory name as
`evidence_pack_id`, import the selected `fname_root_slots` address, and import the selected
`gobjects_candidates` address. If a pack has multiple roots or GObjects candidates, pass
`--evidence-pack-fname-root-label <label>` or `--evidence-pack-gobjects-label <label>`.
Explicit CLI core, identity, FName-root, or GObjects values must match the manifest or
regeneration aborts.
Likewise, `build_core_dump_evidence_pack.py --gobjects-sample-index` now requires an
explicit `--fname-root-slot` for the sampled artifact and resolves sampled names only
through explicit roots in that mode. Use `--scan-fname-tables` or a static derivation
first, then pass the verified root to GObjects/UObject sampling.
Core evidence pack manifests now expose a structured `promotion_gate` with `ready=false`
and blocker reasons. A generated static xref artifact removes the static-xref blocker only
when at least one non-oversized anchor window exists; empty or contaminated xref groups
remain non-actionable.

`scripts/build_static_global_promotion_evidence.py` is the static-only starting point for
global candidate evidence. It avoids core dumps and runtime probes: given a binary,
candidate addresses, and either generated or pre-existing `objdump`/`readelf` text, it
records binary SHA256, command/artifact provenance, copied/generated artifact SHA256, ELF
LOAD segment and section membership, xrefs, RIP-relative versus immediate-reference
counts, and a per-candidate static contract. Detailed xref records are enriched with
instruction segment/section membership and match-kind metadata. Candidate kinds are
fail-closed: labels must resolve to `gobjects` or `fname_root` through recognized naming
or an explicit `--candidate-kind LABEL=gobjects|fname_root`, so an ambiguous alias cannot
fall into a weaker generic-global path. `gobjects` candidates require coherent root,
chunks, count, and serial xrefs where each required field has at least one RIP-relative reference
to that concrete target from an executable ELF segment and executable section, and all
four fields must appear in one non-oversized instruction window. A single root reference,
globally dispersed field references, immediate-only field references, same-instruction
immediate literals, or data range references are not enough. The tool also rejects
`/servidor/ark` paths and
duplicate candidate labels/addresses so analysis is performed on copied artifacts with
unambiguous manifests. Pre-existing `objdump`/`readelf` inputs must carry a sibling
`<artifact>.provenance.json` sidecar with `verified=true`, `binary_sha256` matching the
requested binary, and `artifact_sha256` matching the copied text; missing, malformed,
unverified, or mismatched provenance adds `unverified_static_artifact_provenance`
blockers. Direct or symlinked sidecars under `/servidor/ark` are rejected before reads,
matching the copied-artifact path policy. The builder writes matching provenance sidecars
next to every generated or verified copied static artifact in its output directory, so
those artifacts can be reused as pre-existing inputs without falling back to manifest-only
provenance. Its top-level
`promotion_gate.ready` remains `false` because
static evidence alone must not promote `GNames`/`GObjects` into runtime contracts; use it
to make the independent static path reproducible before combining it with second-source
artifact evidence. Static GObjects xrefs may include additive semantic metadata such as
`semantic`, `semantic_summary`, and coherent-window `role`/`context` fields to explain
lookup, bootstrap, init, reset, or destructor-like evidence; these fields are heuristics
for reviewer orientation and must not weaken blockers or make static-only evidence
promotable.

Static preflight on 2026-05-29 used a copied offline `ShooterGameServer` artifact with
SHA256 `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520` and wrote
`/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/`. The
candidate `fname_root=0x5956f30` satisfied its static contract with 25 RIP-relative
root-slot xrefs. The candidate `gobjects=0x595b7e0` remained blocked:
`missing_gobjects_coherent_field_window`. It had code-backed xrefs for the expected
field targets (`root`, `chunks`, `count`, and `serial`), but no non-oversized coherent
window that tied all four fields together. Treat this as a useful static rejection, not
promotion evidence; the next GObjects task is to inspect the relevant xref clusters and
candidate field offsets before using the address in a second-source core intake.

ReflectionScanner analyzer JSON and `build_reflection_evidence_pack.py` manifests also
expose a structured fail-closed `promotion_gate`. Even when analyzer status is
`research-candidate`, the gate keeps `ready=false`, `promotable.gnames=false`, and
`promotable.gobjects=false` until a second isolated capture or independent static path is
recorded. ReflectionScanner packs explicitly block GObjects promotion because they do not
prove object-array layout, membership, or object/name resolution.

## P1 Module Fixture Matrix

| Module | Current Best Use | Second-Source Promotion Gate | Still Blocked |
| --- | --- | --- | --- |
| `sdk.inventory` | Internal marker-gated metadata observer for `CanUse` and `AllowRemoteAddToInventory`. | Second-source UFunction shape for both targets plus one approved debug observation with budget and no value logging. | Item ids, inventory contents, cooldown bypass policy, callbacks, return overrides. |
| `sdk.structures` | Best current public-resource candidate as a metadata-only observer surface. Clean vanilla second-source shape is accepted for all six `structure-observer-intake` targets. | Runtime payload copy/redaction tests, C ABI registration/unregister tests, approved debug observation with budget, and explicit policy that pincode/player identity remain redacted. | Placement/build/snapping mutation, raw pincode values, player identity, return overrides. |
| `sdk.dinos` | Offline fixtures for compact passenger/carry shapes. | Second-source shape for `AddPassenger` and `AllowCarryCharacter`; no arrays or actor identity exposure. | Taming mutation, attacks, controller stats, generic actor refs. |
| `sdk.buffs` | Offline internal recognizer plus 6 real `PrimalBuff` fixtures cover compact bool returns, object/class metadata, and a zero-param target. The compact three-target set has accepted second-source layout evidence. | Further promotion needs either a separate broader offline target set for the remaining fixture-backed shapes or copied-payload/runtime policy; keep ranges internal and metadata-only. | Runtime hooks, callbacks, return override, mutation of add/prevent/upload policy, raw `UObject*`/`UClass*`, mission/grapple/companion semantics, arrays/strings. |
| `sdk.tribes` | Offline permission/membership fixtures. | Second-source scalar permission targets with identity redaction policy. | Tribe logs, online arrays, player/tribe identity callbacks. |
| `sdk.missions` | Offline lifecycle fixtures. | Second-source compact lifecycle targets with arrays metadata-only. | Usable-item arrays, mission payload dispatch. |
| `sdk.transfers` | UFunction fixtures plus two candidate ScriptStruct fixtures. | Second-source layout-only comparison for `ARKTributeDino` and `ArkTributePlayerData`. | `ItemNetInfo`, upload/download runtime dispatch, nested arrays/strings. |

The executable named target sets for the current P1 offline intakes are:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set buff-compact-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set dino-compact-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set mission-compact-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set tribe-compact-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set structure-observer-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set transfer-ufunction-intake
```

These target sets are readiness/intake tools, not release gates by default. Add
`--fail-on-readiness-gaps` only when reviewing a second-source candidate root for that
module.

Current intake ledger:

| Target Set | Type | Priority | Base Fixtures | Second Source | Action Allowed Now | Still Blocked |
| --- | --- | --- | --- | --- | --- | --- |
| `minimal-second-source-intake` | UFunction | P0 | 4/4 comparable | accepted direct-root report: 4/4, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, blockers=[] | Use only as compact inventory/structure UFunction layout evidence. | Public callbacks, mutation APIs, broad module promotion, GObjects, resource identity, return override, and object identity. |
| `structure-observer-intake` | UFunction | P1 | 6/6 comparable | historical clean triage accepted 6/6; rerun required from copied offline artifacts | Current public promotion exception is copied/redacted `GameplayPolicyEvent`, not a raw StructureEvents API. | Public StructureEvents, pincode/value logging, mutation, raw object identity. |
| `buff-compact-intake` | UFunction | P1 | 3/3 comparable | accepted report: 3/3, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, blockers=[] | Use only as compact buff UFunction layout evidence. | Runtime hooks, return overrides, object/class exposure, public Buff SDK. |
| `dino-compact-intake` | UFunction | P1 | 2/2 comparable | accepted report: 2/2, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, blockers=[] | Use only as compact dino UFunction layout evidence. | Actor identity, taming mutation, attacks, public Dino SDK. |
| `mission-compact-intake` | UFunction | P1 | 4/4 comparable | accepted report: 4/4, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, blockers=[] | Keep as lifecycle/array-metadata layout evidence only; mission is the cleaner post-RC module candidate. | Array payload dispatch, mission value callbacks, object identity, mutation, and return overrides. |
| `tribe-compact-intake` | UFunction | P1 | 5/5 comparable | accepted report: 5/5, `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, blockers=[] | Keep as permission/identity-risk layout evidence only; split scalar targets before any public work. | Tribe logs, online arrays, player/tribe identity callbacks, strings/arrays, mutation, and return overrides. |
| `transfer-ufunction-intake` | UFunction | P1/P2 | 7/7 comparable | missing 7/7 | Keep offline; useful for transfer surface mapping. | Upload/download runtime dispatch and transfer payload decoding. |
| `transfer-scriptstruct` | ScriptStruct | Opt-in | 2/2 comparable | missing 2/2 | Layout-only second-source comparison when an artifact exists. | Nested arrays, strings, `ItemNetInfo`, runtime transfer payloads. |

Target-set acceptance is per set and per function. `minimal-second-source-intake` is the
compact UFunction layout gate for two inventory functions and two structure functions; it
is not a public Inventory API, not a public StructureEvents API, and not evidence for
other functions in either module. The only current public gameplay event exception is
`GameplayPolicyEvent`, and it is backed by `structure-observer-intake` plus copied/redacted
POD ABI and lifecycle evidence, not by the broader minimal intake result.

Current offline property-class risk across committed intake fixtures, including
`transfer-scriptstruct` fields and observed array-inner candidates:

| Property Class | Observed Count | Current Support | Promotion Risk |
| --- | ---: | --- | --- |
| `BoolProperty` | 36 | Comparable as offset/size metadata in sanitized fixtures. | Do not copy as public values until native-bool versus bitfield semantics and allow/deny meaning are verified per target. |
| `ObjectProperty` | 26 | Metadata-only target/class/outer reference validation. | Do not expose raw object pointers, ownership, lifetime, or player/item/dino identity through the ABI. |
| `StrProperty` | 8 | Metadata-only `FString` shape evidence. | Decode, copy ownership, encoding, and redaction policy are required before exposing text values or names. |
| `IntProperty` | 7 | Compact scalar metadata is suitable for layout comparison. | Treat `pinCode`, item ids, spawn ids, bed ids, player data ids, and similar values as sensitive; never log or copy raw values publicly. |
| `ArrayProperty` | 7 | Inner/type candidate metadata only. | Arrays remain blocked for public callbacks until element ownership, bounds, deep copying, and redaction are designed. |
| `UInt32Property` | 4 | Compact scalar or array-inner metadata is suitable for layout comparison. | Identity-like values such as `DinoID*` and `OnlinePlayerIDs` require redaction and policy before exposure. |
| `ClassProperty` | 3 | Metadata-only class reference validation. | Do not expose raw class pointers or use them as stable plugin identifiers. |
| `StructProperty` | 3 | Struct type candidate metadata only. | Nested layout/value decoding remains blocked until second-source struct evidence exists. |
| `ByteProperty` | 3 | Compact scalar or array-inner metadata is suitable for layout comparison. | Enum/byte semantics are not a public contract yet, especially for permissions and byte payloads. |
| `FloatProperty` | 3 | Compact scalar metadata is suitable for layout comparison. | Values remain layout-only until copied-data and ABI policy are explicit. |
| `UInt64Property` | 2 | Compact scalar metadata is suitable for layout comparison. | Treat identity-like or transfer values as sensitive until policy and ownership are explicit. |
| `NameProperty` | nested only | Depends on accepted FName/GNames evidence. | Tags and names may leak identity or gameplay state; require FName second-source evidence and redaction policy. |

The property matrix is an offline planning aid. It does not make any target promotable and
must not be used to bypass `promotion_gate.ready=false`, second-source artifact identity,
or the copied-data ownership review.

## Minimal Second-Source Intake

Use this first intake before expanding more gameplay surfaces. It is deliberately small:
two inventory functions and two structure functions that already have primary snapshots and
internal observer plans, without arrays, strings, raw identity exposure, callbacks, return
overrides, or gameplay mutation.

| Module | First Targets | Why These First |
| --- | --- | --- |
| `sdk.inventory` | `PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory` | Compact item-policy shapes with existing internal observer gates; useful for validating bool/scalar layout comparison before item contents or inventory arrays. |
| `sdk.structures` | `PrimalStructure.AllowStructureAccess`, `PrimalStructure.IsAllowedToDemolish` | Compact structure access/demolish shapes with existing marker-gated observation policy; avoids pincode and placement/build mutation surfaces. |

Current primary readiness against committed fixtures alone, without passing a candidate
second-source snapshot root:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set minimal-second-source-intake \
  --fail-on-readiness-gaps
```

Expected base-root-only diagnostic result, not the accepted direct-root report:

```text
readiness targets=4 comparable=4 blocked=0 second_source_status=missing_candidate_root gate_mode=second_source_promotion
promotion_gate ready=false blockers=missing_second_source:4
ufunction:sdk_inventory targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
  target=obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowRemoteAddToInventory comparable=true second_source=missing
  target=obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse comparable=true second_source=missing
ufunction:sdk_structures targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
  target=obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess comparable=true second_source=missing
  target=obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish comparable=true second_source=missing
```

This base-root-only diagnostic still exits non-zero because no candidate root is supplied.
It is not the accepted direct-root report from
`/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`.
Omit `--fail-on-readiness-gaps` only when generating an informational gap report that must
not block the current core-first release gate.

When a second sanitized snapshot root exists, compare only this intake first:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <second-source-ufunction-snapshots> \
  --target-set minimal-second-source-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

Promotion requires all four targets to be `accepted` by
`compare_reflection_snapshots.py`, with non-empty sanitized artifact identity on both
roots: `generated_by`, `artifact_kind`, `artifact_sha256`, `capture_id`, and
`evidence_pack_id`. The
second source must use distinct `artifact_sha256`, `capture_id`, and `evidence_pack_id`;
missing or shared identity remains `inconclusive`, even when layouts match. Evidence must
also record binary SHA, Obelisk commit, artifact path, commands, reject conditions checked,
and an explicit statement that no live server was touched unless the artifact came from an
operator-approved debug capture. Even after layout acceptance, runtime observation remains
separate and must use a named debug instance, marker/env/SHA/budget gates, no value logging,
and no public SDK callbacks.

An accepted minimal report only promotes those four sanitized UFunction layouts for
offline reflection confidence. The two inventory targets remain internal recognizer
evidence only, and the two structure targets are a subset of the structure observer
evidence; neither half creates public callbacks, mutation, return overrides, resource
identity, or UE pointer exposure.

## Structure Observer Intake

Use this focused intake when evaluating all currently recognized structure observer
UFunctions after the minimal inventory/structure gate is understood. It names the six
structure functions already covered by primary fixtures and internal recognizer tests:

- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`
- `PrimalStructure.SetVariant`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureSeating.CanSeat`

Current base-readiness command:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set structure-observer-intake \
  --fail-on-base-readiness-gaps
```

Expected current result: six comparable `sdk_structures` targets, zero blocked base
targets, and six missing second-source targets. This confirms committed fixture coverage;
it does not promote the structure observer to public SDK readiness.

Internal StructureEvents promotion remains blocked until `structure-observer-intake`
second-source evidence is accepted and a separate approved metadata-only runtime
observation confirms the exact target set with no sensitive values, mutation, raw object
identity, or payload logging. Until then, do not add
`OBELISK_API_CAPABILITY_STRUCTURE_EVENTS`, `ObeliskStructureEvent*`, or
`RegisterOnStructureEvent`/`UnregisterStructureEvent` plugin API. The internal dispatcher
may only carry copied scalar values after the original `ProcessEvent` path ran.

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
readiness targets=2 comparable=2 blocked=0 second_source_status=missing_candidate_root gate_mode=second_source_promotion
promotion_gate ready=false blockers=missing_second_source:2
scriptstruct:sdk_transfers targets=2 comparable=2 blocked=0 second_source=accepted:0,rejected:0,inconclusive:0,missing:2
  target=obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino comparable=true second_source=missing
  target=obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData comparable=true second_source=missing
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
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

## Evidence Pack Checklist

Every second-source note or evidence pack should record:

- target instance and map;
- ARK binary path and SHA256;
- Obelisk commit;
- sanitized artifact identity fields: `artifact_kind`, `artifact_sha256`, `capture_id`,
  and `evidence_pack_id`;
- snapshot producer field `generated_by`;
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

A clean vanilla second-source core is now available as
`vanilla-gdb-arkserver2-TheIsland-20260529T012853Z`, with core SHA256
`56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb` and matching ARK
binary SHA256 `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
Pre-capture evidence says there was no Obelisk env, maps, or process evidence. A later
direct-root execution under
`/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`
accepted `minimal-second-source-intake` for the four compact inventory/structure
`UFunction` layouts with `promotion_gate.ready=true` and no blockers. That result does not
promote FName/GObjects runtime contracts, ResourceHandle, object identity, mutation, return
override, or public SDK readiness.
