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
serial-candidate values. Later broad serial scans supersede that narrow conclusion for the
full object array: `FUObjectItem+0x8` has nonzero serial candidates in both copied cores.
That is serial-only evidence and does not prove public `ResourceHandle` readiness. Static
global evidence also remains blocked unless it proves a coherent root/chunks/count/serial
field window for the same candidate.

If redacted field-window evidence clears `missing_gobjects_coherent_field_window`, that is
only a static-contract improvement. It may set the coherent-window booleans in this
evaluator, but it must not flip `post_callback_resource_handle_ready`; serial/lifetime
revalidation and `uobject_flags_validity_semantics_unproven` remain independent blockers.

The expected active blockers depend on the input pack:

- `uobject_flags_validity_semantics_unproven`
- lifetime/reuse behavior not proven

Older or narrower packs may also report `missing_gobjects_coherent_field_window`; the
`resource-handle-nonzero-revalidation-20260529T060741Z` pack clears that static-contract
blocker for its inputs and leaves only `uobject_flags_validity_semantics_unproven`.

Treat `zero_or_missing_fuobjectitem_serial_candidates` as historical or narrow-sample
evidence when reviewing old evaluator output. A current evaluator should distinguish
`no_nonzero_serial_candidates_found` from expected mixed zero/nonzero serials in broad
object-array scans.

`post_callback_resource_handle_ready` remains `false`. ResourceHandle, object identity,
mutation, and return override surfaces remain unpromoted.

## Validation

No runtime/server action is required. Inputs under `/servidor/ark` are rejected unless
they resolve under `/servidor/ark/workspace-offline`.
