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

## Serial Policy Result

The existing identity-complete evaluator artifact is safe for
`scripts/build_resource_handle_serial_policy.py` to consume:

```text
/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-identity-complete-failclosed-20260530T165521Z/resourcehandle-revalidation.json
```

Validation summary:

- source consume gate accepted with `--root /home/flowcommunity-ark/obelisk-artifacts`
- source file sha256:
  `9eb1fcd672327d1509becc9fd9d2937fc227f5cdb6fc23403a79a99a115fb833`
- source `output_artifact_identity.artifact_sha256`:
  `d358b16e4c70ef3b320e00143f3ed2bd41581c4d40045974b02ef61c55b4dab2`
- identity inputs complete: `missing_or_partial_input_count=0`,
  `invalid_input_count=0`
- reconciliation samples: `accepted_sample_count=44`,
  `serial_candidate_nonzero_count=44`, `serial_candidate_zero_count=0`,
  `serial_candidate_missing_count=0`
- source keeps `promotion_ready=false`, `public_resource_handle_ready=false`,
  and `post_callback_resource_handle_ready=false`
- source has `serial_reuse_or_wraparound_policy_present=false`, so the builder is not
  consuming a pre-existing serial-policy overclaim

Generated artifact:

```text
/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-serial-policy-20260530T190642Z/
```

Command:

```bash
python3 scripts/build_resource_handle_serial_policy.py \
  --revalidation /home/flowcommunity-ark/obelisk-artifacts/resourcehandle-identity-complete-failclosed-20260530T165521Z/resourcehandle-revalidation.json \
  --capture-id resourcehandle-serial-policy-20260530T190642Z \
  --evidence-pack-id resourcehandle-serial-policy-20260530T190642Z \
  --output /home/flowcommunity-ark/obelisk-artifacts/resourcehandle-serial-policy-20260530T190642Z/serial-policy.json
```

Result:

```text
serial-policy.json sha256=a4fe1b1390103b31e49c241deadc3bca0f12adc37d4a1efa306a02dbf8de3532
output_artifact_identity.artifact_sha256=01cb5335dca3fe6301ddee007284e61044d30b288a0f2c33e160df562344406d
schema=obelisk.internal-uobject-revalidation-serial-policy.v1
status=accepted_internal_candidate_policy
promotion_ready=false
public_resource_handle_ready=false
post_callback_resource_handle_ready=false
promotion_gate.ready=false
promotion_gate.blockers=candidate_only_serial_reuse_wraparound_policy
```

The decision table rejects zero serials, serial mismatches, unknown wraparound, slot reuse
without a freshly proven serial, and post-callback/cross-frame use. Only a fresh nonzero
serial match in the same hook/callback frame reaches `allow_candidate_frame_local_only`,
and output remains copied bool/reason or Obelisk-owned copied data only.

Follow-up gate integration registered
`obelisk.internal-uobject-revalidation-serial-policy.v1` as a manifest schema. The
generated serial-policy report now passes consume mode when provided as a manifest:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/resourcehandle-serial-policy-20260530T190642Z/serial-policy.json \
  --mode consume
```

Result:

```text
accepted mode=consume blockers=0
```

Promote mode remains blocked:

```text
promote_mode_serial_policy_candidate_only
promote_mode_manifest_has_non_claims
```

Use `--manifest` for this structured JSON report. The generic `--artifact` path still
requires a `.provenance.json` sidecar because it validates unstructured files rather than
schema-aware JSON reports.

## Serial Policy Gate Audit

An offline audit of the generated serial-policy artifact confirmed the schema-aware gate
path against the durable artifact:

```text
/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-serial-policy-20260530T190642Z/serial-policy.json
```

Validation:

- `sha256sum serial-policy.json`:
  `a4fe1b1390103b31e49c241deadc3bca0f12adc37d4a1efa306a02dbf8de3532`
- `SHA256SUMS` records the same file hash.
- `output_artifact_identity.artifact_sha256`:
  `01cb5335dca3fe6301ddee007284e61044d30b288a0f2c33e160df562344406d`
- consume gate with `--manifest` and `--root /home/flowcommunity-ark/obelisk-artifacts`:
  `accepted`, blockers `0`
- promote gate with the same manifest: blocked by
  `promote_mode_serial_policy_candidate_only` and `promote_mode_manifest_has_non_claims`
- no `/servidor/ark`, local artifact paths, or ready-state overclaims were present in the
  serial-policy JSON.

Focused tests passed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_resource_handle_serial_policy
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_validate_offline_artifact_gate
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_public_sdk_guardrails.PublicSdkGuardrailTests.test_resource_handle_serial_policy_tooling_stays_internal_candidate_only
```

Audit result: consume acceptance is valid for indexing and planning only. The immediate
strict gate blocker remains `promote_mode_serial_policy_candidate_only`. For the
ResourceHandle promotion lane, the next strict evidence blocker is rejected runtime object
samples plus runtime serial reuse/wraparound semantics; the accepted serial-policy
artifact only defines fail-closed policy and explicitly does not prove runtime reuse
safety, public lookup safety, persistent handles, identity, mutation, return overrides,
or public `ResourceHandle`.

## Next Repo-Local Improvement

After serial-policy artifact acceptance, the smallest useful repo-local improvement is a
schema/test-plan clarification for the two future runtime artifacts, not a new scan,
runtime observer, or promotion note. The goal is to define what a later approved run must
redact and what the offline consume gate must reject.

Candidate fixture scope:

- `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1` should require a
  redacted run identity, source serial-policy artifact identity, at least one rejected
  object-present row, canonical reject reason, `FUObjectItem+0x8` match status only, and
  `UObject+0x8` candidate reject bits as booleans only.
- `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1` should require a
  redacted run identity, source serial-policy artifact identity, at least one same-frame
  fresh nonzero match result, at least one zero/missing/mismatch rejection result, and
  `unknown_wraparound_reject=true` unless a separate written plan proves otherwise.

Negative fixture scope:

- reject raw UE pointers, object indices, serial values, class/name/outer paths, player or
  gameplay payloads, persistent lookup tokens, `/servidor/ark` paths, `FUObjectItem+0xc`
  treated as serial, `promotion_ready=true`, `public_resource_handle_ready=true`,
  `post_callback_resource_handle_ready=true`, cross-frame acceptance, broad tracing
  evidence, or promote-mode readiness.

Keep this as offline schema/gate planning only. It should not add C++ observer code,
server markers, live-ops instructions, ReflectionScanner usage, public SDK fields,
identity lookup, mutation, return override, or a `ResourceHandle` promotion claim.

## Future Runtime Observation Plan

This section is a planning artifact only. It does not approve server operations, marker
edits, restarts, `/servidor/ark` reads or writes, ptrace/gcore, ReflectionScanner,
scanner-like probes, broad `ProcessEvent` tracing, Discord notice, GitHub publication, or
public API promotion.

The minimal future live-ops request should be a single approved debug/development
runtime-observation window whose only purpose is to produce two redacted internal
evidence artifacts:

1. `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1`
2. `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`

Both artifacts must remain consume-only planning inputs with
`promotion_ready=false`, `public_resource_handle_ready=false`, and
`post_callback_resource_handle_ready=false`.

### Approval Blockers

The plan is blocked until an operator-approved live-ops brief names all of the following:

- exact debug/development target instance and map, with no production/shared target reuse;
- ARK binary SHA256 and Obelisk commit expected for the run;
- restart/start/stop window, rollback steps, and final stable-posture expectation;
- exact env+marker gates for the observer, including plugins disabled unless the brief
  explicitly justifies a narrower plugin set;
- copied-log and artifact output locations, plus the offline promotion path for any raw
  server-local capture;
- max runtime duration, max sampled events, max rejected rows, and max log lines;
- whether players can be present and, if so, the approved notice path.

Without that brief, there is no approval to execute any part of this plan.

### Runtime Gate Shape

Use a new default-off debug observer profile rather than scanner/debug-control tooling.
The profile should be enabled only by the approved env+marker pair, require the exact
binary SHA, require an explicit short allowlist of `fname_index` values, and use a hard
budget. It must never run as broad event discovery.

The observer may inspect only the already reviewed internal candidate state needed to
decide fail-closed behavior:

- candidate slot in bounds;
- `FUObjectItem` readable by the runtime's normal guarded read path;
- object pointer non-null or null as a rejected condition;
- `FUObjectItem+0x8` nonzero status and match/mismatch status only;
- `FUObjectItem+0xc` recorded only as `observed_unknown_dword_present`, never as serial;
- `UObject+0x8` candidate bits `0x100` and `0x4000` as redacted boolean masks;
- whether the candidate was accepted frame-local, rejected by flag policy, rejected by
  serial policy, rejected by missing/null object, or rejected by post-callback use.

Logs and artifacts must not contain raw UE pointers, object indices, serial values,
FName indices beyond the approved allowlist label, class/name/outer paths, player text,
inventory payloads, gameplay payloads, or persistent lookup tokens.

### Rejected Runtime Object Samples

The rejection-samples artifact is accepted only if it contains at least one redacted row
where all of the following are true:

- the observation came from the approved SHA, commit, instance, marker profile, and
  allowlisted callback;
- the candidate slot was in bounds and structurally readable;
- the serial candidate was nonzero and matched `FUObjectItem+0x8`;
- the object pointer was present;
- `UObject+0x8` contained a candidate reject bit covered by the current fail-closed
  policy;
- the observer rejected the candidate and emitted only a copied reason/category.

Reject the artifact if any row requires raw values to interpret, includes public identity,
comes from an unapproved target/profile, relies on broad tracing, normalizes unknown bits
into accepted lifecycle names, or treats mutation-window evidence as lookup safety.

### Runtime Serial Semantics

The serial-semantics artifact is accepted only as a negative/fail-closed semantics pack.
It should answer whether runtime observations contradict the accepted serial policy, not
try to force a public handle promotion.

Minimum useful rows:

- a fresh same-frame nonzero serial match that reaches
  `allow_candidate_frame_local_only`;
- a same-frame serial mismatch or missing/zero serial that rejects;
- if naturally observed within the approved budget, a slot/object transition where reuse
  is rejected unless a freshly proven nonzero serial match exists.

Wraparound does not need to be observed. If the run cannot prove wraparound behavior, the
artifact must explicitly preserve `unknown_wraparound_reject=true`. Any wraparound claim
requires a separate written plan because forcing wraparound or allocation churn is outside
this minimal observation window.

Reject the artifact if it exposes serial values, treats `FUObjectItem+0xc` as serial,
claims persistent handle validity, accepts cross-frame lookup, or relaxes the existing
zero/missing/mismatch/reuse-without-fresh-serial rejection table.

### Post-Run Gates

After the approved run, the lead should promote only copied logs or redacted artifacts to
an approved offline root, then run schema-aware consume validation. Promotion validation
must still block unless a later separate contract also proves public lookup/privacy,
post-callback lifetime, lifecycle-name correlation, ABI/SDK guardrails, and versioned
operator safety.

Expected immediate result even after a successful minimal run:

```text
consume gate: accepted
promote gate: blocked
required blockers still present:
  public_resourcehandle_policy_missing
  no_public_resource_handle_contract
  post_callback_lifetime_policy_unproven
  no_version_matched_source_decompiler_correlation_for_public_lifecycle_names
  public lookup/privacy/ABI gate missing
```

The only blockers this plan is intended to narrow are
`no_rejected_runtime_object_samples` and the runtime-observed portion of
`no_serial_reuse_or_wraparound_policy`. It must not unlock public `ResourceHandle`,
public GObjects lookup, object identity, mutation, return override, persistent handles,
or Plugin Hub SDK exposure.
