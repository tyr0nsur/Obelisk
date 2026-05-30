# ResourceHandle Strict Static Global Refresh Plan

## Objective

Turn the next ResourceHandle static-global audit into an executable offline plan for the
current baseline, without promoting public `ResourceHandle`, public `GObjects`, object
identity, lookup, mutation, return override, or post-callback lifetime.

Baseline reviewed in this worktree:

```text
repo: /home/flowcommunity-ark/Obelisk
branch/head: main 89060ef
binary_sha256: 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
binary: /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
```

## Inputs Found

These inputs exist under `/home/flowcommunity-ark/obelisk-artifacts` or repo
`docs/scripts` and are enough to regenerate a strict static-global manifest with the
current `artifact_identity` implementation:

```text
/home/flowcommunity-ark/Obelisk/scripts/build_static_global_promotion_evidence.py
/home/flowcommunity-ark/Obelisk/scripts/validate_offline_artifact_gate.py
/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump.provenance.json
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt.provenance.json
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt.provenance.json
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-xrefs.json
```

Related ResourceHandle/GObjects inputs found, but not yet strict identity-ready as
current inputs:

```text
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/gobjects-reconciliation.json
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/artifact-pack.manifest.json
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-serial-scan-primary-20260530T000000Z/primary-full-serial-flags.redacted.json
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-serial-scan-primary-20260530T000000Z/artifact-pack.manifest.json
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/artifact-pack.manifest.json
```

Those packs record useful internal evidence: `44/44` accepted flag-`0x4000` GObjects
samples with nonzero `FUObjectItem+0x8`, serial-scan consume readiness, and accepted
candidate-only UObject flag-policy evidence. They still should not be treated as strict
ResourceHandle promotion evidence.

## Inputs Missing

These concrete inputs were not found in the allowed artifact/docs/scripts surface:

```text
No /home/flowcommunity-ark/obelisk-artifacts/** JSON with schema obelisk.fuobjectarray-field-window-redacted.v1
No durable /home/flowcommunity-ark/obelisk-artifacts/** FUObjectArray Ghidra stdout/radare2 window pair for scripts/convert_fuobjectarray_field_window_probe.py
No current static-global manifest under /home/flowcommunity-ark/obelisk-artifacts with top-level artifact_identity
No current gobjects-reconciliation.json under /home/flowcommunity-ark/obelisk-artifacts with top-level artifact_identity
No current uobject-flag-policy.redacted.json under /home/flowcommunity-ark/obelisk-artifacts with top-level artifact_identity
```

Consequence: the strict static-global refresh is executable now, but it will keep the
`gobjects` candidate blocked unless the missing redacted FUObjectArray field-window JSON
is supplied. A strict ResourceHandle revalidation run with `--require-artifact-identity`
will also remain blocked until the reconciliation and flag-policy inputs are regenerated
with complete identity.

## Executable Static-Global Refresh

This command uses only existing inputs and current script identity support. It copies the
existing objdump/readelf artifacts, verifies their provenance sidecars, writes a fresh
top-level `artifact_identity`, and keeps promotion blocked.

```bash
python3 scripts/build_static_global_promotion_evidence.py \
  --binary /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  --candidate fname_root=0x5956f30 \
  --candidate gobjects=0x595b7e0 \
  --candidate-kind fname_root=fname_root \
  --candidate-kind gobjects=gobjects \
  --output-dir /tmp/obelisk-static-global-strict-refresh-20260530T000000Z \
  --objdump /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump \
  --readelf-programs /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt \
  --readelf-sections /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt \
  --capture-id primary-static-global-20260530 \
  --evidence-pack-id static-global-preflight-20260529-strict-refresh \
  --json
```

Then consume-gate the regenerated manifest:

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --manifest /tmp/obelisk-static-global-strict-refresh-20260530T000000Z/manifest.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json
```

Expected result for the run above:

```text
static-global artifact_identity: present and hash-checked by the gate
fname_root static_contract.satisfied: true
gobjects static_contract.satisfied: false
gobjects blocker: missing_gobjects_coherent_field_window
promotion_gate.ready: false
```

Lead execution result on commit `96c656079f88`:

```text
output_dir: /tmp/obelisk-static-global-strict-refresh-20260530T000000Z
artifact_identity.artifact_sha256: 35692df0f5a5348771504d0fa2131e78cc3e08495e28080a3be2c5fd2595ba11
manifest_sha256: 39ca36f1b853e57e41be1c1d0dd424cf1dc6dbab06da0604a9ff7336e0e1f21f
static_xrefs_sha256: ccf8991fa9cdc465f565a64e83bbb00688469eb856a74957253d59dc77bb2be4
fname_root static_contract.satisfied: true
gobjects static_contract.satisfied: false
gobjects blocker: missing_gobjects_coherent_field_window
promotion_gate.ready: false
consume_gate with --root /tmp: accepted
```

The first consume-gate attempt without `--root /tmp` correctly blocked because the
default approved workspace root is `/servidor/ark/workspace-offline`; this was a path
policy check, not an evidence failure. The artifact remains a temporary fail-closed audit
output, not a durable promotion input, until a matching workspace/offline-artifact location
and missing field-window evidence are supplied.

Lead follow-up with the durable workspace field-window input:

```text
field_window_input: /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/field-window/fuobjectarray-field-window.redacted.json
field_window_schema: obelisk.fuobjectarray-field-window-redacted.v1
field_window_sha256: cf1d430833d232ecbfda8ba8791730f1c56032b6e0f18d93cf5ab7c92c679d57
output_dir: /tmp/obelisk-static-global-strict-with-field-window-20260530T000000Z
artifact_identity.artifact_sha256: ce5eca1f8ba35297e00005628a301f5a55dd3c4e6724d44904ae70250c62e78c
manifest_sha256: b1466b6dcc5995f00f953d54859e101a9c78f00ca8f9eca823897b4b71eabd53
fname_root static_contract.satisfied: true
gobjects static_contract.satisfied: true
gobjects blocker: cleared missing_gobjects_coherent_field_window
promotion_gate.ready: false
promotion_gate blocker: static_only_evidence
consume_gate with --root /tmp: accepted
```

This clears only the static `gobjects` coherent field-window blocker for the reviewed
binary/candidate pair. It still does not promote public `GObjects`, `ResourceHandle`,
lookup, identity, lifetime, mutation, return override, or UE call replay.

Durable neutral workspace refresh: the same static-global refresh was regenerated under
`/servidor/ark/workspace-offline/static-global-strict-with-field-window-20260530T000000Z`
and accepted by `validate_offline_artifact_gate.py --root /servidor/ark/workspace-offline
--mode consume`. Prefer this neutral root for future strict static-global citations. A
parallel path whose directory name included `resourcehandle` was rejected by the static
global gate with `static_global_public_overclaim_resourcehandle` because manifest path
strings themselves are scanned for public overclaims.

## Blocked Field-Window Upgrade

`scripts/build_static_global_promotion_evidence.py` can clear only the
`missing_gobjects_coherent_field_window` static-contract blocker if supplied with a
matching redacted field-window JSON through this argument:

```text
--fuobjectarray-field-window-evidence
```

No valid existing path for that argument was found under
`/home/flowcommunity-ark/obelisk-artifacts` during the first read-only artifact search.
A valid pre-strict-identity redacted field-window artifact was later found under the
approved offline workspace at `/servidor/ark/workspace-offline` and consumed in the
follow-up result above.

Do not invent a path for this input. If a new run is needed, first create or durably copy
a real `obelisk.fuobjectarray-field-window-redacted.v1` JSON under an approved offline
workspace, then rerun the static-global command above with that existing path.

## Strict ResourceHandle Evaluator Path

After strict static-global, strict ResourceHandle evaluation should require identity on
all supplied inputs:

```bash
python3 scripts/evaluate_resource_handle_revalidation.py \
  --reconciliation /home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/gobjects-reconciliation.json \
  --static-global-evidence /tmp/obelisk-static-global-strict-refresh-20260530T000000Z/manifest.json \
  --uobject-flag-policy /home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json \
  --require-artifact-identity \
  --output /tmp/obelisk-resourcehandle-strict-revalidation-20260530T000000Z/resourcehandle-revalidation.json
```

Expected result with the current found inputs:

```text
promotion_gate.ready: false
blocker: missing_or_partial_artifact_identity for current reconciliation and flag-policy inputs
blocker: missing_gobjects_coherent_field_window unless field-window evidence is added
blocker: uobject_flags_validity_semantics_unproven / lifecycle blockers remain
```

The evaluator command is therefore useful as a fail-closed audit, not as a promotion run,
until identity-ready reconciliation and flag-policy reports are regenerated.

## What This Still Does Not Demonstrate

Even a strict static-global manifest with complete `artifact_identity` does not prove:

- public `ResourceHandle` or public `GObjects`;
- post-callback lookup or persistent object lifetime;
- public object identity, player identity, inventory/item identity, or lookup tokens;
- mutation safety, return override safety, or UE call replay;
- cross-binary portability;
- public UE lifecycle flag names;
- serial reuse, wraparound, or stale-handle rejection policy;
- negative runtime samples for rejected objects.

If the missing field-window JSON is later supplied and accepted, it can clear only the
static `missing_gobjects_coherent_field_window` blocker for the matching binary and
candidate. Promotion must still stay blocked by `static_only_evidence` and ResourceHandle
lifecycle/flag-policy blockers.
