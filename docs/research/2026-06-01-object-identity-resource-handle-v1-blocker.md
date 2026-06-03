# Object Identity and ResourceHandle v1 Blocker

## Summary

The SDK map already excludes raw UE pointers, lookup, and `ResourceHandle` from many
surfaces, but object identity is a cross-cutting blocker and should be treated as its own
SDK design lane before any public API relies on post-callback object correlation.

This is planning guidance only. It adds a `post-v1` completion blocker to
`public_sdk_surfaces.json`, does not promote an object identity API, and does not change
v1 completion status or stable claim eligibility.

## Why It Matters

Object identity affects multiple high-demand SDK families:

- structures: ownership, limits, build placement, no-collision policy;
- inventory/items: item handles, mutation, rewards, kits;
- dinos and tribes: ownership, policy, colors/cosmetics, carry rules;
- buffs/status and missions/transfers: event correlation across callbacks;
- economy/mobility: rewards, homes, teleport, safe zones, and area policy.

Without a proven lifecycle contract, a copied callback cannot safely expose a stable object
handle, lookup key, or post-callback reference. Current public surfaces must continue to
use copied/redacted scalar data and metadata descriptors only.

## Required Future Evidence

Before any public object identity/lookup lane exists, Obelisk needs:

- lifecycle and invalidation semantics for UObject-backed identities;
- reuse/wraparound behavior and negative samples for stale objects;
- callback-scope vs post-callback validity rules;
- privacy and redaction boundaries for owner/player/tribe-related identity;
- owner-token scoped lookup/cleanup policy if lookup is ever exposed;
- ABI layout and installed-SDK consumer coverage;
- explicit exclusions for raw UE pointers, raw params, FName/GObjects indices, and direct
  mutation.

Until then, `ResourceHandle`, object lookup, and persistent object identity remain blocked
across structures, inventory, dinos, tribes, buffs, missions, transfers, economy, mobility,
and area-policy work.

## Next Offline Cohort

The next useful offline-only package is a negative-sample cohort for zero-serial
`FUObjectItem` entries from the existing two cores. Current redacted serial scans show a
clear gap: `rejected_sample_count=0`, while both cores include many serial-zero entries.

Use existing offline artifacts only:

- `/servidor/ark/workspace-offline/resource-handle-nonzero-revalidation-20260529T060741Z/readiness-redacted.json`
- `/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/vanilla-serial-scan.redacted.json`
- `/servidor/ark/workspace-offline/resource-handle-serial-scan-20260529/second_source-serial-scan.redacted.json`
- `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
- `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`

The candidate cohort should record object items with non-null object pointers and
`FUObjectItem+0x8 == 0` as stale/invalid handle evidence, contrasted with known positive
samples such as index `50834` with serial `1001`. This still does not prove UObject flag
validity semantics, runtime reuse/wraparound behavior, public lookup, or `ResourceHandle`
promotion.

## 2026-06-01 Zero-Serial Negative Cohort Candidate

Added `scripts/build_resource_handle_zero_serial_negative_samples.py` to make the next
negative-sample package reproducible from the two copied cores without broad rediscovery.
The helper scans index order only through the known positive anchor by default
(`--anchor-index 50834`) and treats `FUObjectItem+0x8` as a candidate `uint32` serial
field. It emits candidate-only JSON with `status=candidate_blocked`; it does not expose
lookup, mutation, public `ResourceHandle`, or runtime lifecycle semantics.

Command run:

```bash
python3 scripts/build_resource_handle_zero_serial_negative_samples.py \
  --core vanilla=/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --core second_source=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --core-sha256 vanilla=56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb \
  --core-sha256 second_source=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78 \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --anchor-index 50834 \
  --negative-limit 8
```

Result: `deterministic_negative_cohort=true` for both sources. Each source scanned
`50835` indices, saw `50835` non-null candidate UObjects, collected the first 8
zero-serial negative samples, and found the positive anchor at index `50834` with
serial `1001`.

| source | core sha256 | fname table | zero-serial cohort | positive anchor |
| --- | --- | --- | --- | --- |
| vanilla | `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb` | `0x5a94660` | indexes `0..7`, all `membership=candidate-uobject`, `item_dword_0x8=0` | index `50834`, `LinkerLoad`, `item_dword_0x8=1001`, `item_dword_0xC=116` |
| second_source | `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78` | `0x3dff0660` | indexes `0..7`, all `membership=candidate-uobject`, `item_dword_0x8=0` | index `50834`, `LinkerLoad`, `item_dword_0x8=1001`, `item_dword_0xC=114` |

The first 8 zero-serial names/classes are stable across both cores:
`/Script/CoreUObject` (`Package`), `Object` (`Class`), `/Script/ShooterGame`
(`Package`), `AhoCorasickMatch` (`Class`), `/Script/Engine` (`Package`), `Actor`
(`Class`), `Controller` (`Class`), and `/Script/AIModule` (`Package`).

Remaining blockers are unchanged: this cohort is useful negative evidence for a
fail-closed serial contract, but it does not prove stale-object lifecycle behavior,
serial reuse or wraparound, UObject flag validity semantics, callback-scope validity,
owner-token cleanup, public lookup, or ABI-safe `ResourceHandle` promotion.

## 2026-06-01 Offline Gate Hardening Audit

Audit after `e9cf787` found that runtime rejection/serial-semantics schemas already
validate source serial-policy artifact identity, redacted run identity, non-claims, and
candidate-only promote blocking. The remaining repo-local gap was the zero-serial cohort:
the builder emitted a useful candidate JSON, but it was not a first-class consume-gate
schema and still carried a raw `core_path` field.

The next offline hardening is now in place:

- `scripts/build_resource_handle_zero_serial_negative_samples.py` emits
  `promotion_ready=false`, `public_resource_handle_ready=false`,
  `post_callback_resource_handle_ready=false`, `promotion_gate.ready=false`, redacts core
  paths, and can bind output to `output_artifact_identity`.
- `scripts/validate_offline_artifact_gate.py` supports
  `obelisk.resource-handle-zero-serial-negative-samples.v1` in consume mode, verifies the
  canonical output identity, requires verified core hashes, deterministic zero-serial
  rows, a nonzero positive anchor, no raw `core_path` field, required non-claims, and
  blocks promote mode as candidate-only.

This does not supply runtime rejected-object samples or runtime serial reuse/wraparound
semantics. It only makes the existing offline zero-serial cohort reproducible and
gate-checkable without turning it into object identity or public `ResourceHandle`
evidence.

## 2026-06-01 Evaluator Non-Substitution Hardening

`scripts/evaluate_resource_handle_revalidation.py` now accepts optional
`--zero-serial-negative-samples` inputs for
`obelisk.resource-handle-zero-serial-negative-samples.v1`. The evaluator validates the
artifact as candidate-only offline evidence, reports only counts and artifact hashes, and
emits `offline_zero_serial_negative_samples_summary` with explicit non-substitution rows:

- zero-serial offline samples do not satisfy
  `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1`;
- zero-serial offline samples do not satisfy
  `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`.

The runtime evidence booleans remain false:
`runtime_rejection_samples_present=false`,
`runtime_serial_semantics_present=false`, and
`runtime_resourcehandle_promotion_evidence_complete=false`. The top-level blockers remain
the exact blockers needed for future approved runtime work:
`no_rejected_runtime_object_samples` and `no_serial_reuse_or_wraparound_policy`.

Invalid zero-serial inputs are named separately with
`invalid_zero_serial_negative_samples_candidate`, so a malformed or overclaiming offline
cohort cannot mask the runtime blockers or look like accepted rejected-object runtime
evidence.

## 2026-06-01 Runtime Manifest Preflight Hardening

Audit after the evaluator non-substitution pass found one repo-local ambiguity left for a
future approved runtime window: the rejected-object and serial-semantics manifests were
candidate-only, redacted, and promote-blocked, but did not carry a first-class preflight
checklist that named the paired runtime manifest and explicitly marked the runtime
evidence package incomplete.

`scripts/validate_offline_artifact_gate.py` now requires
`runtime_evidence_preflight` on both future runtime schemas:

- `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1`
- `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`

The preflight must record the ResourceHandle runtime-semantics candidate scope, the rule
that both runtime manifests are required and still candidate-only, the exact paired
runtime schema, approved-window/bounded-allowlist/redaction/source-policy checks, and the
zero-serial offline non-substitution acknowledgement. It must also keep
`promotion_evidence_complete=false`, `authorizes_runtime_work=false`, and
`public_resource_handle_ready=false`.

This is still offline validation only. It does not approve a server window, does not run
runtime probes, and does not promote `ResourceHandle`; it prevents an incomplete future
runtime artifact from looking like complete promotion evidence.

## 2026-06-01 Post Player-Identity Route Audit

The ResourceHandle blocker does have a narrow route after player identity, but it is not
another FName/GObjects/core/serial scan. The preceding player-identity lane must first
produce approved copied runtime principal lifecycle evidence for the exact
`ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` observer window. That
evidence may only establish an opaque, process-local principal lifecycle boundary; it does
not promote object identity, lookup, `ResourceHandle`, mutation, return override, or
GObjects.

After that player-principal boundary is accepted, the next ResourceHandle package should
be a separate operator-approved runtime window with a bounded allowlist and copied,
redacted outputs only. It should reuse the existing offline inputs as source policy:
accepted serial-policy evidence, zero-serial non-substitution evidence, static
`FUObjectItem+0x8` serial-candidate evidence, and the current `0x595b7e0` GObjects
research candidate only as offline context. Do not repeat broad FName, GObjects, core, or
serial rediscovery for the current binary hash unless existing evidence is contradicted.

The minimum runtime evidence pair is:

- `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1`: at least one
  object-present row where the candidate slot is in bounds, `FUObjectItem` is readable,
  `FUObjectItem+0x8` is a nonzero match, `FUObjectItem+0xC` remains
  `observed_unknown_dword_present`, a candidate `UObject+0x8` reject bit
  (`0x100` or `0x4000`) is present, the decision is `reject`, and copied output is only a
  reason category. Summary must keep `accepted_rows=0`.
- `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`: at least one
  fresh same-frame nonzero-match row accepted only as
  `allow_candidate_frame_local_only`, plus at least one negative reject row such as
  `zero_serial`, `serial_mismatch`, `wraparound_unknown`,
  `slot_reuse_without_fresh_serial`, or `post_callback_or_cross_frame`. The manifest must
  keep `unknown_wraparound_reject=true`, `cross_frame_lookup=reject`, and
  `FUObjectItem+0xC` as `unknown_not_serial_evidence`.

Both runtime manifests must carry `runtime_evidence_preflight`, name each other as the
paired runtime schema, keep `promotion_evidence_complete=false`,
`authorizes_runtime_work=false`, and `public_resource_handle_ready=false`, and pass the
offline artifact gate in consume mode only. Even if both manifests pass, they are still
candidate runtime semantics, not public lookup or a promoted `ResourceHandle` API; public
promotion would still require a fail-closed lookup/owner-token contract, ABI and
installed-SDK consumer coverage, privacy review, and lifecycle/restart/plugin-reload
cleanup rules.

## 2026-06-01 Runtime Pair Gate Audit

Audit of the minimum runtime evidence pair found one repo-local hardening gap: each
runtime schema could already validate as candidate-only with `promotion_ready=false` and
the paired schema named in `runtime_evidence_preflight`, but the artifact gate did not
require both manifests to appear in the same validation run. That made the checklist
machine-readable but not fully machine-enforced.

`scripts/validate_offline_artifact_gate.py` now adds an aggregate pair-presence check for
`obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1` and
`obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`. A half-pair now
blocks with `runtime_evidence_pair_missing`; the accepted consume-mode path must provide
both manifests together. This still does not promote `ResourceHandle`, authorize runtime
work, or make the pair public evidence. It only prevents a single candidate runtime
artifact from passing as if the minimum runtime package were complete.

## 2026-06-01 ResourceHandle Runtime-Pair Intake Recheck

Focused offline intake after the runtime-pair gate audit found no additional small
template or consume-checker gap to close for the future rejected-runtime-object-samples
and serial-reuse/wraparound blocker. The existing gate already requires the two future
runtime schemas to be supplied together, keeps each schema candidate-only, verifies
redacted run identity and source serial-policy identity, rejects raw UE/object/serial
disclosures, blocks protected-path strings, rejects broad tracing/scanner/core-capture
claims, and fails promote mode.

The rejected hypothesis for this pass is that another offline zero-serial, GObjects,
FName, core, or serial artifact would advance the blocker. It would not. The current
offline scaffolding can only consume a future approved runtime pair; it cannot synthesize
the missing runtime observations.

## 2026-06-03 Revalidation Evaluator Public-Lookup Boundary

Focused offline audit found one narrow gate gap in
`scripts/validate_offline_artifact_gate.py` for
`obelisk.resource-handle-revalidation-evaluator.v1`: consume mode required
post-callback and flag-semantics readiness to stay false, but did not independently
reject top-level public `ResourceHandle`/promotion readiness or nested `evidence_checks`
that counted candidate-only serial/object evidence as public lookup/runtime identity.

The gate now rejects evaluator manifests that set `promotion_ready`,
`public_resource_handle_ready`, public contract/policy booleans, runtime rejection or
serial-semantics booleans, runtime promotion-complete booleans, or zero-serial
non-substitution rows as satisfied. This preserves the current blocked outcome: offline
serial/GObjects/object candidates can support internal accounting only, not public lookup,
public object identity, post-callback handles, mutation, or return override.

Exact next evidence needed remains unchanged:

- one consume-accepted
  `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1` manifest with an
  object-present rejected row, redacted run identity, accepted source serial-policy
  identity, `FUObjectItem+0x8` recorded only as match status, `FUObjectItem+0xC` recorded
  only as unknown dword present, candidate `UObject+0x8` reject bits as booleans, and
  `accepted_rows=0`;
- one consume-accepted
  `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1` manifest from the
  same redacted runtime window and source policy, with at least one fresh same-frame
  nonzero-match frame-local allow row, at least one negative reject row, cross-frame
  lookup rejected, and `unknown_wraparound_reject=true`;
- both manifests must be validated together in one consume-mode gate run and must still
  fail promote mode as candidate-only.
