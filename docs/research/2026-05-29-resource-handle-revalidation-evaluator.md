# ResourceHandle Revalidation Evaluator

## Summary

`scripts/evaluate_resource_handle_revalidation.py` is an offline, redacted aggregator for
existing `GObjects`/`FUObjectItem` reconciliation reports and optional static global
evidence. It is intentionally a readiness blocker, not a promotion tool.

The evaluator emits counts, booleans, blocker strings, and available artifact SHA-256
identity only. It does not emit paths, object names, class/outer names, indices, pointers,
FName data, FUObjectItem addresses, or raw serial values.

## Current Posture

With the narrow copied-offline reconciliation reports, accepted samples still had zero
serial-candidate values. Existing serial-scan/fullscan and strict reconciliation
artifacts supersede that narrow conclusion for the current binary hash:
`FUObjectItem+0x8` has accepted nonzero serial candidates, including identity-complete
internal evidence. That is historical/internal serial evidence only; it is not a request
to run another broad serial sweep and it does not prove public `ResourceHandle`
readiness.

The static coherent field-window and artifact-identity gaps have been narrowed by later
post-RC artifacts for internal planning. They must still not flip
`post_callback_resource_handle_ready`; rejected runtime object samples, runtime
serial-reuse/wraparound semantics, lookup privacy, public lifecycle naming, and API/SDK
contracts remain independent blockers.

The expected active blockers depend on the input pack:

- `no_rejected_runtime_object_samples`
- `no_serial_reuse_or_wraparound_policy`
- `uobject_flags_validity_semantics_unproven`
- public lookup/privacy/API contract not proven

Older or narrower packs may also report `missing_gobjects_coherent_field_window`; the
`resource-handle-nonzero-revalidation-20260529T060741Z` pack clears that static-contract
blocker for its inputs and leaves only `uobject_flags_validity_semantics_unproven`.

Treat `zero_or_missing_fuobjectitem_serial_candidates` as historical or narrow-sample
evidence when reviewing old evaluator output. A current evaluator should distinguish
`no_nonzero_serial_candidates_found` from expected mixed zero/nonzero serials in broad
object-array scans.

Do not answer any of those historical blocker names by creating a fresh broad scan for the
current binary hash. Use the canonical post-RC inputs and target only the future
approved-runtime semantic artifacts.

`post_callback_resource_handle_ready` remains `false`. ResourceHandle, object identity,
mutation, and return override surfaces remain unpromoted.

## 2026-05-30 Fail-Closed Evaluator Extension

`scripts/evaluate_resource_handle_revalidation.py` now keeps measuring the blocker
instead of promoting a handle. The current extension remains internal/offline and emits
`promotion_ready=false`, `public_resource_handle_ready=false`, and
`post_callback_resource_handle_ready=false`.

Required non-claims should include:

- `does_not_unlock_resource_handle`
- `does_not_promote_gobjects_lookup`
- `does_not_promote_public_object_identity`
- `does_not_claim_post_callback_lookup`
- `does_not_name_ue_lifecycle_flags_publicly`
- `does_not_allow_mutation_or_return_override`
- `does_not_replace_rejected_runtime_object_samples`

Required blockers should include:

- `no_public_resource_handle_contract`
- `public_resourcehandle_policy_missing`
- `no_post_callback_lifetime_contract`
- `post_callback_lifetime_policy_unproven`
- `no_serial_reuse_or_wraparound_policy`
- `no_version_matched_source_decompiler_correlation_for_public_lifecycle_names`
- `no_rejected_runtime_object_samples`

Even strong serial/GObjects evidence may set only internal measurement booleans. It must
not flip public or post-callback readiness until lifecycle, reuse/wraparound, lookup
privacy, and post-callback validity contracts are separately proven.

The evaluator adds those blockers both to the top-level `blockers` set and to
`lifetime_blocker_summary.blockers`. Existing dynamic evidence blockers such as
`zero_or_missing_fuobjectitem_serial_candidates`,
`missing_gobjects_coherent_field_window`, and
`uobject_flags_validity_semantics_unproven` remain measurable and may change with
stronger offline inputs, but the required lifetime blockers remain until a separate
public ResourceHandle contract is designed and validated.

## 2026-05-30 Internal UObject Revalidation Candidate

The evaluator can now consume an optional redacted
`obelisk.uobject-flag-policy-report.v1` via `--uobject-flag-policy` and emit an
`internal_uobject_revalidation_candidate` section. This section is an internal static
candidate only. It records counts, hashes, the redacted `0x100`/`0x4000` policy candidate,
and a fail-closed contract:

- lifetime: `frame_local_only`
- post-callback lookup: `rejected`
- output: `copied_bool_or_obelisk_owned_data_only`
- public API: `not_promoted`

For the durable artifact
`/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json`,
the evaluator derives that contract from the candidate matrix because the artifact predates
the embedded `internal_revalidation_contract` field. This does not promote
`ResourceHandle`, object identity, lookup, mutation, return override, SDK surface, or UE
lifecycle names. `uobject_flags_validity_semantics_proven`,
`public_resource_handle_ready`, and `post_callback_resource_handle_ready` remain `false`.

## Validation

No runtime/server action is required. Inputs under `/servidor/ark` are rejected unless
they resolve under `/servidor/ark/workspace-offline`.
