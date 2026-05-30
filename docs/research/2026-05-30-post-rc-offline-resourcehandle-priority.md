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

Among those semantic gaps, the next offline artifact should be the post-callback rejection
contract. It can use the accepted internal candidate already present in the evaluator
output to state, in redacted/fail-closed form, that `InternalUObjectRevalidationCandidate`
is frame-local only, post-callback lookup is rejected, output remains copied bool or
Obelisk-owned copied data, and no public `ResourceHandle`, GObjects lookup, identity,
mutation, or return override is promoted. This advances the lifecycle contract without
inventing runtime samples or relaxing the public API blocker.

## Post-Callback Rejection Contract

The post-callback rejection contract is now preserved at:

```text
/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-post-callback-contract-20260530T171910Z/
```

It is generated from the identity-complete fail-closed evaluator artifact and uses the
internal schema:

```text
obelisk.internal-uobject-revalidation-post-callback-contract.v1
```

Result:

```text
post-callback-contract.json sha256=caaad8b80608e6af603da413f021ae43c8a44a55a3c1964f9e4e69eee10c4fd0
output_artifact_identity.artifact_sha256=a80e8597a027fd8e7a3c5bb2c42abfc7523e1dc13c69111629aed3450d8260d5
consume-gate.status=accepted
promote-gate.status=blocked
promote blockers=promote_mode_post_callback_contract_candidate_only,promote_mode_manifest_has_non_claims
promotion_ready=false
public_resource_handle_ready=false
post_callback_resource_handle_ready=false
post_callback_lookup_ready=false
```

The contract is a negative/lifetime artifact only. It proves that the internal candidate
is frame-local and that post-callback lookup/use must fail closed. It does not clear
runtime object samples, serial reuse/wraparound, public lifecycle names, public
`ResourceHandle`, object identity, GObjects lookup, mutation, return override, or Plugin
Hub identity requirements.

## 2026-05-30 Audit Update

Current blocker map after the post-callback contract:

- `GObjects`/`FUObjectArray` is strong internal offline evidence for the reviewed binary
  hash, with strict static field-window support and identity-complete evaluator inputs,
  but remains non-public and static/core-evidence-only.
- `FUObjectItem+0x8` is the favored serial-backed dword; `FUObjectItem+0xc` remains
  unknown and must be recorded neutrally.
- `0x100` and `0x4000` remain internal flag-policy candidates only. The policy rejects
  `0x100` and rejects `0x4000` by default unless a reviewed helper mode proves otherwise.
- The post-callback rejection contract proves only frame-local/internal fail-closed
  behavior. It does not create public lookup, public identity, or post-callback handles.
- Remaining blockers are serial reuse/wraparound policy, rejected runtime object samples,
  public lifecycle-name correlation, public lookup/privacy policy, and promotion-mode
  ABI/SDK/lifecycle guardrails.

Next offline action: produce a candidate-only serial reuse/wraparound policy artifact
from the bounded weak-helper assign/validate paths and existing identity-complete
evaluator inputs. The artifact should state that zero serials, serial mismatches, unknown
wraparound, and slot reuse without a freshly proven serial all fail closed, while keeping
`promotion_ready=false`, `public_resource_handle_ready=false`, and
`post_callback_resource_handle_ready=false`. Do not rerun broad FName/GObjects/core scans
for this step.

## Serial Reuse/Wraparound Candidate Policy

The offline builder for the next candidate-only step is:

```bash
python3 scripts/build_resource_handle_serial_policy.py \
  --revalidation <identity-complete-resourcehandle-revalidation.json> \
  --capture-id <safe-capture-id> \
  --evidence-pack-id <safe-evidence-pack-id> \
  --output <tmp-or-approved-offline-root>/serial-policy.json
```

It emits:

```text
obelisk.internal-uobject-revalidation-serial-policy.v1
```

This artifact is a policy contract, not runtime proof. The builder requires an
identity-complete fail-closed evaluator source, accepted internal candidate evidence,
nonzero serial candidates, no zero or missing serial candidates, and no pre-existing
serial reuse/wraparound overclaim in the source. It does not read cores, rerun scanners,
or use server paths.

The emitted policy is deliberately strict:

- zero serial: reject
- missing serial: reject
- serial mismatch: reject
- unknown wraparound: reject
- slot reuse without a freshly proven serial for the current slot: reject
- post-callback or cross-frame use: reject

Only a fresh nonzero serial match in the same hook/callback frame can reach
`allow_candidate_frame_local_only`, and that still produces copied bool/reason or
Obelisk-owned copied data only. The report keeps `promotion_ready=false`,
`public_resource_handle_ready=false`, `post_callback_resource_handle_ready=false`, and
`promotion_gate.ready=false`.

Remaining non-claims are unchanged for public `ResourceHandle`, public GObjects lookup,
object identity, mutation, return override, persistent handles, and public SDK exposure.
The policy narrows the serial reuse/wraparound design gap but does not prove runtime
reuse semantics or public lookup safety.
