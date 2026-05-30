# ResourceHandle Fail-Closed Evaluator Audit

## Objective

Capture the 2026-05-30 strict offline `ResourceHandle` evaluator result as durable
negative evidence. This note records the command, inputs, result, non-claims, and next
step without copying the raw JSON report.

## Environment

```text
repo: /home/flowcommunity-ark/Obelisk
commit: 6f42f8ba01f8
evaluator_output: /tmp/obelisk-resourcehandle-durable-strict-audit-20260530.json
generated_at_utc: 2026-05-30T15:11:33+00:00
binary_sha256: 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

This was an offline audit only. It did not touch live ARK instances, runtime C++,
public headers, plugins, or server state.

## Inputs

```text
/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/gobjects-reconciliation.json
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json
```

Input summary from the evaluator:

```text
reconciliation reports: 1
static-global evidence reports: 1
uobject flag-policy reports: 1
accepted reconciliation samples: 44/44
membership pass count: 44
nonzero serial candidates: 44
zero or missing serial candidates: 0
static gobjects candidates: 1
coherent gobjects field window proven: false
artifact identity required: true
complete identity inputs: 0
missing or partial identity inputs: 3
invalid identity inputs: 0
```

## Reproduction

```bash
python3 scripts/evaluate_resource_handle_revalidation.py \
  --reconciliation /home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/gobjects-reconciliation.json \
  --static-global-evidence /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json \
  --uobject-flag-policy /home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json \
  --require-artifact-identity \
  --output /tmp/obelisk-resourcehandle-durable-strict-audit-20260530.json
```

A local repro check using the same inputs matched the durable audit on the decision
fields, blocker list, report counts, reconciliation summary, static-global summary,
evidence checks, lifetime blocker summary, non-claims, and artifact identity summary.

## Result

```text
promotion_ready: false
public_resource_handle_ready: false
post_callback_resource_handle_ready: false
uobject_flags_validity_semantics_proven: false
```

Blockers:

```text
missing_gobjects_coherent_field_window
missing_or_partial_artifact_identity
no_post_callback_lifetime_contract
no_public_resource_handle_contract
no_rejected_runtime_object_samples
no_serial_reuse_or_wraparound_policy
no_version_matched_source_decompiler_correlation_for_public_lifecycle_names
post_callback_lifetime_policy_unproven
public_resourcehandle_policy_missing
uobject_flags_validity_semantics_unproven
```

The useful positive evidence is limited to internal/offline accounting: accepted
reconciliation samples are present, membership checks pass for those samples, and all
accepted samples carry nonzero `FUObjectItem+0x8` candidate values. That does not clear
the static coherent-window, artifact-identity, UObject flag semantics, or lifetime
policy blockers.

## No-Claims

This audit does not:

- unlock `ResourceHandle`;
- promote GObjects lookup;
- promote public object identity;
- claim post-callback lookup;
- name UE lifecycle flags publicly;
- allow mutation or return override;
- replace rejected runtime object samples.

## Next Step

Regenerate the reconciliation, static-global evidence, and UObject flag-policy inputs
with complete top-level `artifact_identity`, using the strict field-window-backed
static-global artifact where appropriate. Then rerun the evaluator with
`--require-artifact-identity`. Even if identity and the coherent field window pass, keep
promotion blocked until rejected runtime object samples, serial reuse/wraparound policy,
version-matched lifecycle-name correlation, and post-callback lifetime rules are proven.

## Decision

```text
resourcehandle_audit_captured=yes
```
