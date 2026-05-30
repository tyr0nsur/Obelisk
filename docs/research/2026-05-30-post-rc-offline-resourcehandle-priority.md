# Post-RC Offline ResourceHandle Priority

## Summary

After the core-first RC gate, the highest-ROI offline reversing path is not another broad
FName, GObjects, or UFunction scan for the current binary hash. Those inputs are already
good enough for internal planning. The remaining ResourceHandle blocker is semantic:
`uobject_flags_validity_semantics_unproven`.

The next useful artifact should narrow when `UObject+0x8` flags require fail-closed
handling while keeping `ResourceHandle`, object identity, lookup, mutation, return
override, and UE lifecycle names unpromoted.

Current state: use `InternalUObjectRevalidationCandidate` as the internal design label
for this work. Do not call it `ResourceHandle` in code, APIs, or plugin-facing docs until
post-callback lifetime, reuse, privacy, and rejection semantics are proven by a separate
promotion gate.

## Recommended Candidate-Only Artifact

Build a fresh `obelisk.uobject-flag-policy-report.v1` with:

- `promotion_ready=false`
- `post_callback_resource_handle_ready=false`
- `0x100` treated only as an internal hard-invalid candidate
- `0x4000` treated only as a strict-invalid or mode-dependent candidate
- no mutation-window-only evidence treated as lookup, identity, lifecycle, or mutation
  safety

Use the existing bounded offline path:

```bash
python3 scripts/build_uobject_flag_policy_report.py \
  --binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --weak-helper-caller-mode /servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/weak-helper-caller-mode.redacted.json \
  --window weak_helper_reject_0x100=<tmp-window> \
  --window strict_0x4000_behavior=<tmp-window> \
  --window gobjects_backed_0x4000_skip=<tmp-window> \
  --window gc_static_0x100_support=<tmp-window> \
  --output <tmp-output>/uobject-flag-policy-report.redacted.json

python3 scripts/validate_offline_artifact_gate.py \
  --manifest <tmp-output>/uobject-flag-policy-report.redacted.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json > <tmp-output>/gate-consume.json
```

Keep outputs in `/tmp` or another approved offline root for the first pass. Do not write
new runtime/server artifacts and do not use ReflectionScanner, ptrace, gcore, markers, or
server restarts for this step.

## Non-Claims

This does not promote:

- public `ResourceHandle`
- post-callback object lookup
- public object identity
- GObjects promotion
- mutation or return override
- named UE lifecycle flag semantics
- mutation safety or mutation APIs from flag transition windows
- `0x4000` as a universal rejection flag outside reviewed helper modes

If the consume gate fails, treat the artifact as invalid evidence rather than partially
accepted.

## 2026-05-30 Follow-Up Result

A first pass against the existing redacted weak-helper artifact failed closed because the
artifact did not embed caller rows or source provenance. The raw sidecars already existed
under the offline workspace, so the weak-helper report was regenerated in `/tmp` with
provenance and six caller rows, then consumed by a fresh `uobject-flag-policy-report.v1`
also written under `/tmp`.

Result:

- consume gate: accepted
- promote gate: blocked as expected
- promote blockers: `promote_mode_uobject_flag_policy_candidate_only` and
  `promote_mode_manifest_has_non_claims`
- public helper identifier: `weak_helper_flag_policy_candidate`
- public output: no raw helper addresses, raw UE lifecycle names, object indices, serials,
  pointers, or local paths

This is useful internal ResourceHandle evidence because it narrows the lifecycle/flag
policy blocker, but it remains candidate-only. It still does not promote public
`ResourceHandle`, object lookup, identity, mutation, return override, or named UE lifecycle
semantics.

## Fail-Closed Contract Clarification

Any future internal revalidation prototype must remain frame-local and fail closed. The
only acceptable internal shape before promotion is:

- Name: `InternalUObjectRevalidationCandidate`, not `ResourceHandle`.
- Lifetime: valid only inside the same hook/callback frame for copied-data decisions; it
  must reject post-callback lookup.
- Inputs: internal index/serial evidence plus binary SHA and consumed artifact identity;
  never expose UE pointers, GObjects indices, serials, class/name/outer values, or lookup
  tokens to plugins.
- Acceptance checks: supported SHA, accepted consume gate, coherent GObjects evidence,
  in-bounds chunk/item, readable `FUObjectItem`, nonzero serial, serial match at the
  current candidate slot, non-null `UObject*`, and plausible membership.
- Flag policy: reject `UObject+0x8 & 0x100`; reject `UObject+0x8 & 0x4000` by default.
  Tolerating `0x4000` requires a specific reviewed helper mode proving that mode; absence
  of that proof is rejection.
- Output: a copied boolean/reason or Obelisk-owned copied data only. No identity,
  persistent handle, public lookup, mutation, return override, or raw UE object escape.

`mutation_windows` or flag transition reports may show where bits are set or cleared, but
they do not prove lookup safety, mutation authority, post-callback lifetime, public
validity semantics, or a public lifecycle name. Keep `promotion_ready=false`,
`public_resource_handle_ready=false`, and `post_callback_resource_handle_ready=false`
until a separate promotion contract supplies negative runtime samples, lifecycle/reuse
policy, and privacy-safe lookup semantics.

## Current Canonical Input

Use the durable rich-provenance refresh as the current canonical internal static input:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/
```

The pack now includes `artifact-pack.manifest.json` and `SHA256SUMS`. Its consume gate is
accepted, its promote gate remains blocked, and the manifest explicitly keeps public
ResourceHandle, public GObjects, object identity, post-callback lookup, lifecycle names,
mutation, return override, and SDK exposure as non-claims.

The current sample-report refresh that combines the rich transition matrix with the
canonical policy pack is:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-sample-refresh-20260530T112500Z/
```

`uobject-flag-sample-report.json` has SHA256
`520278d7388a7740bdd9e39d7ea055fa3b1c7262ff2403af68cbabbef6ececbf`.
The consume gate is accepted and the promote gate is blocked with the expected
candidate-only/non-claims blockers. Treat this as internal static sample evidence only;
it does not clear `uobject_flags_validity_semantics_unproven` or promote
`ResourceHandle`.

Superseded inputs should stay historical only:

- `/servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-static-negative-regenerated-20260529T1910Z/`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-semantic-decompiler-20260529T155658Z/uobject-flag-semantic-correlation.json`

Do not rerun broad FName, GObjects, or core scans for this path unless the binary hash
changes or new evidence contradicts the canonical pack.

## Identity-Complete Fail-Closed Evaluation

The ResourceHandle revalidation lane now has a strict identity-complete evaluator artifact
that keeps the result fail-closed:

```text
/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-identity-complete-failclosed-20260530T165521Z/
```

Inputs:

- `gobjects/gobjects-reconciliation.json`: regenerated from the existing 44
  `rh_flag4000_*` sample indices with `--strict-artifact-identity`.
- `uobject-policy/uobject-flag-policy.redacted.json`: regenerated from the durable
  rich-provenance input root with `--strict-artifact-identity`.
- `/servidor/ark/workspace-offline/static-global-strict-with-field-window-20260530T000000Z/manifest.json`:
  consumed read-only in place because it is already under the approved offline workspace
  and carries complete `artifact_identity`.

Command:

```bash
python3 scripts/evaluate_resource_handle_revalidation.py \
  --reconciliation "$OUT/gobjects/gobjects-reconciliation.json" \
  --static-global-evidence /servidor/ark/workspace-offline/static-global-strict-with-field-window-20260530T000000Z/manifest.json \
  --uobject-flag-policy "$OUT/uobject-policy/uobject-flag-policy.redacted.json" \
  --require-artifact-identity \
  --require-output-artifact-identity \
  --artifact-kind obelisk.resource-handle-revalidation-evaluator.v1 \
  --capture-id resourcehandle-revalidation-20260530T165521Z \
  --evidence-pack-id resourcehandle-identity-complete-failclosed-20260530T165521Z \
  --output "$OUT/resourcehandle-revalidation.json"
```

Result:

```text
output_artifact_identity.artifact_sha256=d358b16e4c70ef3b320e00143f3ed2bd41581c4d40045974b02ef61c55b4dab2
artifact_identity.complete_input_count=3
artifact_identity.missing_or_partial_input_count=0
reconciliation_summary.sample_count=44
reconciliation_summary.accepted_sample_count=44
reconciliation_summary.serial_candidate_nonzero_count=44
static_global_evidence_summary.coherent_field_window_proven=true
promotion_ready=false
public_resource_handle_ready=false
post_callback_resource_handle_ready=false
```

Remaining blockers:

```text
no_post_callback_lifetime_contract
no_public_resource_handle_contract
no_rejected_runtime_object_samples
no_serial_reuse_or_wraparound_policy
no_version_matched_source_decompiler_correlation_for_public_lifecycle_names
post_callback_lifetime_policy_unproven
public_resourcehandle_policy_missing
uobject_flags_validity_semantics_unproven
```

This clears the previous missing/partial artifact identity gap for both the evaluator
input set and the evaluator output. It does not clear ResourceHandle promotion.
`InternalUObjectRevalidationCandidate` remains internal, frame-local, and fail-closed;
public `ResourceHandle`, public GObjects, object identity, lookup, mutation, return
override, post-callback handles, and plugin SDK exposure remain blocked.

Next useful work is not more broad static scanning. The remaining evidence gap is semantic:
negative runtime samples, serial reuse/wraparound policy, and a strict post-callback
lifetime/lookup rejection contract before any public identity or lookup surface can be
considered.
