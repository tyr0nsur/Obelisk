# ResourceHandle Serial Scan Gate

Date: 2026-05-29

## Objective

Prepare the offline artifact gate for the next ResourceHandle blocker artifact without
promoting public handles.

## Gate Contract

`obelisk.resource-handle-serial-scan.v1` is accepted in consume mode only when
`flag_rejection_candidate_samples` is non-empty and each candidate has:

- membership pass through GObjects,
- nonzero `FUObjectItem+0x8` serial,
- object pointer present,
- `UObject+0x8` mask `0x100`, `0x4000`, or `0x8000`,
- strict policy result `reject`.

`0x4000` by itself is a candidate in the allow-4000 policy view, so its
`policy_result_allow4000` must be `allow_candidate`. Candidates carrying `0x100` or
`0x8000` must still be rejected in both strict and allow-4000 policy views.

Promote mode is always blocked for this schema.

`core_sha256` identifies the copied core file. `binary_sha256` identifies the matching
ShooterGameServer binary and is required even when no `--expected-binary-sha256` is
passed. `core_path` must be an absolute path under the approved offline workspace and
must not resolve back into protected server storage.

The gate verifies `core_path` exists and that the file's actual SHA256 matches
`core_sha256`; `core_sha256_verified=true` is not accepted as a self-assertion. Scanner
runs intended for gate consumption should use `scripts/scan_resource_handle_serials.py
--gate-ready` with explicit `--core-sha256`, `--binary-sha256`, `--gobjects`,
`--fname-root-slot`, `--offline-root`, and `--output`.

`scan_limit` is required and must match provenance. It is the absolute `GObjects` slot
ceiling used for candidate-index validation. `totals.objects_read` must be less than or
equal to `scan_limit`, but it is not a valid upper bound for sparse candidate indices.

Scanner provenance records the invocation with path arguments redacted. Do not store raw
`/servidor/ark` paths in free-form manifest strings; the gate treats those as protected
path leaks even when `core_path` itself is an approved offline workspace path.

## Non-Claims

This gate does not promote `ResourceHandle`, object identity, public lookup,
post-callback lifetime, mutation, or return override. It only identifies whether a copied
offline scan contains the rejected-object candidate shape needed for the next research
step.

Totals, `flag_mask_samples`, nonzero serial samples, and negative samples do not promote
the schema. The only useful next-step signal is a coherent
`flag_rejection_candidate_samples` entry with membership, serial, object-pointer, mask,
and policy fields aligned.

Readiness booleans such as `public_resource_handle_ready`, `resource_handle_ready`, or
`post_callback_resource_handle_ready` are overclaims anywhere in the manifest. Generic
promotion booleans such as `promotion_ready`, `runtime_ready`, `lookup_ready`,
`mutation_ready`, and `return_override_ready` are also blocked.

The schema remains candidate-only. Status/evidence fields may be omitted or use
`status=candidate_blocked` and `evidence_kind=internal_offline_scan_candidate`; promoted
wording is blocked. Candidate indices must be unique, within `scan_limit`, and carry a
u32 `flags` value; `objects_read` is the count of materialized object entries, not an
absolute `GObjects` slot ceiling.

## 2026-05-30 Existing Core Decision

Do not rerun `scripts/scan_resource_handle_serials.py --gate-ready` on the currently known
two copied TheIsland cores as the next priority. The stronger existing candidate paths are:

```text
/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core
core_sha256=56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb

/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core
core_sha256=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78
```

Both correspond to ShooterGameServer SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, but existing broad
scan/fullscan notes already report no coherent `flag_rejection_candidate_samples` and no
observed `0x100`/`0x4000` mask-positive samples. A `--gate-ready` rerun is therefore
expected to fail with `missing_flag_rejection_candidate_samples` and would mostly spend
time reproducing known negative evidence.

Use these cores for metadata/path reference only. The useful next artifact likely needs a
new controlled copied core/state that actually contains mask-positive objects, or a
separate static/runtime plan that explains how to obtain such a state without weakening
the candidate-only gate.

## 2026-05-30 Primary Core Follow-Up

The only existing copied core not yet covered by `scan_resource_handle_serials.py` is the
primary Ragnarok core:

```text
/servidor/ark/workspace-offline/primary-core-20260527T031311Z/raw/core
core_sha256=1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e
binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
gobjects=0x595b7e0
fname_root_slot=0x5956f30
object_count=1243796
```

Do not run this as a live/server operation; it is an offline core read. Because it may scan
up to 1.24M UObject slots from an 11 GB core, prefer the fast flag/serial path first and
write to a non-server temporary output unless an operator explicitly approves preserving
under the offline workspace:

```bash
python3 scripts/scan_resource_handle_serials.py \
  --core /servidor/ark/workspace-offline/primary-core-20260527T031311Z/raw/core \
  --core-sha256 1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e \
  --binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --max-objects 1243796 \
  --sample-limit 64 \
  --skip-name-resolution \
  --label primary_ragnarok_20260527 \
  --output /tmp/obelisk-primary-resource-handle-serial-scan.redacted.json
```

Run without `--gate-ready` for the first exploratory pass so a negative report is still
written. If it produces coherent `flag_rejection_candidate_samples`, replay with an
approved durable offline output and then validate consume mode. If it also reports
`flags_any=0`, the known copied cores are exhausted for this blocker and the next step is
a separately approved capture/state plan, not another static rerun.

## 2026-05-30 Primary Core Result

The primary-core exploratory scan completed with name resolution disabled and produced
coherent candidate samples:

```text
/tmp/obelisk-primary-resource-handle-serial-scan.redacted.json
sha256=60a5fd8a4940a3f1950e947c837543bafb4b1403a85f21d1568d4a9365ccdca3
```

Key result:

```text
objects_read=1241943
scan_limit=1243796
serial_nonzero=43466
membership_pass_count=1241943
membership_fail_count=0
flags_0x100=0
flags_0x4000=44
flags_0x8000=0
flags_any=44
flag_rejection_candidate_samples=44
consume_gate_expectation.consume_ready=true
consume_gate_expectation.promote_ready=false
```

All 44 coherent candidates are `0x4000` mask candidates with nonzero serials, object
pointers present, GObjects membership pass, strict policy `reject`, and allow-4000 policy
`allow_candidate`. This satisfies the internal consume-mode ResourceHandle blocker
artifact need, but it does not promote public `ResourceHandle`, lookup, object identity,
mutation, return override, or post-callback lifetime safety.

Initial gate replay from `/tmp`:

```text
/tmp/obelisk-primary-resource-handle-serial-scan.consume-gate.json
sha256=99ba196108949a698226fefe6eb4f23cd23ead10e9bd58a8a8ee686b839e85a0
status=accepted

/tmp/obelisk-primary-resource-handle-serial-scan.promote-gate.json
sha256=9011ec3028d3ebcde03f9889c3a94c50a6a2ca9cc08eb751bedfeddc791bacd4
status=blocked
blocker=promote_mode_resource_handle_serial_scan_candidate_only
```

The report and gate outputs were preserved outside Git and outside `/servidor/ark`:

```text
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-serial-scan-primary-20260530T000000Z/
SHA256SUMS sha256=3e5cb6db9572715b38077f79752212823fc1790951ba4045ec72d1adf6b7ffef
artifact-pack.manifest.json sha256=ac88295b9b16d9755858c16fed6377e23adcdfab5f5e0ef55eb17a08ce8d74dc
```

Durable artifact gate replay:

```text
primary-full-serial-flags.redacted.json consume: accepted
primary-full-serial-flags.redacted.json promote: blocked
blocker=promote_mode_resource_handle_serial_scan_candidate_only
```

The gate was adjusted to allow a manifest under a non-server artifact root to reference a
copied core under the approved `/servidor/ark/workspace-offline` root while continuing to
block other protected server paths. Candidate index validation now uses `scan_limit`
because UObject indices are absolute GObjects slots while `objects_read` counts materialized
objects.

## 2026-05-30 Focused Candidate Reconciliation

The 44 primary-core `0x4000` candidates were reconciled with the existing point-in-time
`GObjects` sampler instead of adding a second targeted mode to
`enumerate_core_uobjects.py`:

```bash
python3 scripts/reconcile_gobjects_samples.py \
  --core /servidor/ark/workspace-offline/primary-core-20260527T031311Z/raw/core \
  --gobjects-candidate 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --sample-index rh_flag4000_422460=422460 \
  ... 43 more rh_flag4000_<index>=<index> samples ... \
  --output /tmp/resource-handle-flag4000-targeted-gobjects-names.json
```

Preserved derived artifact:

```text
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/
gobjects-reconciliation.json sha256=cfe272896b8c24aa61a26f26968698f73a626c87103d0de26bf425efb4d1e43f
SHA256SUMS sha256=91246969444eff6d66b9da50c78be0524101048ee84e380a9300b4dd4e897a04
```

Result:

```text
schema=obelisk.gobjects-sample-reconciliation.v1
sample_count=44
accepted_count=44
rejected_count=0
membership_pass_count=44
item_dword_0x8_nonzero_count=44
class_name=ParticleSystemComponent for all 44 samples
object_name=ParticleSystemComponent0 for all 44 samples
outer_name=Text_Actor_C for 40 samples
outer_name=Text_Actor for 4 samples
```

Interpretation:

- The serial-scan candidates are coherent real `GObjects` entries, not broken pointers.
- The candidates cluster tightly around transient-looking `ParticleSystemComponent0`
  instances owned by `Text_Actor` / `Text_Actor_C`.
- This strengthens internal blocker accounting for `UObject+0x8 & 0x4000` and
  `FUObjectItem+0x8` serial-candidate observations.
- It does not promote public `ResourceHandle`, object identity, lookup, lifecycle/reuse
  semantics, mutation, return override, or post-callback validity. The result is still a
  single copied-core, point-in-time reconciliation artifact.
- Further broad ResourceHandle scanning is not a next RC priority from this evidence.
