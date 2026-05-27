# Second-Source Reversing Gap Matrix

## Objective

Convert the broad "get a second source" requirement into concrete acceptance gates for
`FName`/`GNames`, `GUObjectArray`, `UObject`, `UFunction`, and module fixtures. This note is
planning only. It does not authorize server restarts, marker changes, ptrace, `gcore`,
ReflectionScanner, native exec probes, or runtime observation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Current baseline: `20e3b79 Reject invalid runtime marker paths`
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
| `FName` / `GNames` | Primary core has useful FName clues; current live logs without scanner are inconclusive. | `None`, `ClientMessage`, and `ServerChat` resolve through the same bounded table/pool; analyzer has no reject markers; evidence includes binary SHA, Obelisk commit, copied log/core path, and either a second isolated capture or static xref path. | `python3 scripts/analyze_reflectionscanner_capture.py --json --binary <ShooterGameServer> --objdump-xrefs <objdump> <copied-log>`; for core packs, `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --scan-fname-tables --fname-root-slot static_fname_root_slot=0x5956f30 --fname-index None=0 --fname-index ClientMessage=4884 --fname-index ServerChat=9619 --fname-index SetActiveMissionDebugFlags=9622`. | Single-source table, clue swap, implausible counts, readable-printable-memory heuristic, runtime probe rejection ignored. |
| `GUObjectArray` / `GObjects` | `0x595b7e0` is a binary-hash-scoped research-candidate. | Second core or static path shows chunk/root/count/serial behavior; at least two sampled objects round-trip through `InternalIndex`; class and outer checks are plausible through object-array membership. | `python3 scripts/build_core_dump_evidence_pack.py --binary <bin> --core <core> --output-dir <pack> --gobjects-candidate gobjects=0x595b7e0 --gobjects-sample-index 0 --gobjects-sample-index 1 --gobjects-sample-index 25447`. | High object-shape score alone, no `InternalIndex` backref, class/outer merely readable, broad memory scans. |
| `UObject` base | RuntimeReflection has a candidate layout; fixtures validate synthetic and primary-core shapes. | Second source confirms vtable, flags, internal index, class, name, outer; object pointer is reachable from `GObjects[InternalIndex]`. | `python3 scripts/enumerate_core_uobjects.py --core <core> --gobjects 0x595b7e0 --fname-root-slot 0x5956f30 --max-objects 30000 --class-contains Function --json`. | Class pointer not in `GObjects`, outer chain loops, FName only numeric, bad vtable/range. |
| `UFunction` / `UProperty` | Primary core supports property-chain snapshots and internal recognizers. | Second core or static path repeats target identity, outer/class membership, `NumParms`, `ParmsSize`, `ReturnValueOffset`, property names/classes/offsets/sizes. | `python3 scripts/inspect_core_ufunctions.py --core <core> --gobjects 0x595b7e0 --fname-root-slot 0x5956f30 --name-exact <target> --outer-exact <outer> --max-object-scan 30000 --snapshot-json`. | String proximity only, executable-tail heuristic only, chain loops, property count mismatch, offsets outside `ParmsSize`. |

After a second-source snapshot set exists, compare sanitized layouts offline before
updating any module status:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots/<sha-prefix>/<module> \
  --candidate-root <second-source-ufunction-snapshots>/<sha-prefix>/<module>
```

Use `--json` for evidence packs. The comparator ignores commit, metadata, and unstable
FName/GObjects indices by default; it returns `accepted`, `rejected`, or `inconclusive` per
target. Use `--strict-identity-indices` only when intentionally comparing same-binary
identity evidence, not for cross-source layout promotion.

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

## Evidence Pack Checklist

Every second-source note or evidence pack should record:

- target instance and map;
- ARK binary path and SHA256;
- Obelisk commit;
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
4. Only then schedule short, marker-gated TheIsland/debug observation for inventory or
   structures.
5. Define SDK promotion policy after copied-data ownership and ABI lifecycle are proven.

## Current Result

No second source is currently available in-repo. Existing recognizers and observers remain
internal and experimental. The next productive work is either an approved isolated artifact
capture or tooling that makes the second-source comparison deterministic once that artifact
exists.
