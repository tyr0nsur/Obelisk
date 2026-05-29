# ResourceHandle Revalidation Evaluator

## Summary

`scripts/evaluate_resource_handle_revalidation.py` is an offline, redacted aggregator for
existing `GObjects`/`FUObjectItem` reconciliation reports and optional static global
evidence. It is intentionally a readiness blocker, not a promotion tool.

The evaluator emits counts, booleans, blocker strings, and available artifact SHA-256
identity only. It does not emit paths, object names, class/outer names, indices, pointers,
FName data, FUObjectItem addresses, or raw serial values.

## Current Posture

With the current copied-offline reconciliation reports, accepted samples still have zero
serial-candidate values. Static global evidence also remains blocked unless it proves a
coherent root/chunks/count/serial field window for the same candidate.

If redacted field-window evidence clears `missing_gobjects_coherent_field_window`, that is
only a static-contract improvement. It may set the coherent-window booleans in this
evaluator, but it must not flip `post_callback_resource_handle_ready`; serial/lifetime
revalidation and `uobject_flags_validity_semantics_unproven` remain independent blockers.

The expected active blockers are:

- `zero_or_missing_fuobjectitem_serial_candidates`
- `missing_gobjects_coherent_field_window`
- `uobject_flags_validity_semantics_unproven`

`post_callback_resource_handle_ready` remains `false`. ResourceHandle, object identity,
mutation, and return override surfaces remain unpromoted.

## Validation

No runtime/server action is required. Inputs under `/servidor/ark` are rejected unless
they resolve under `/servidor/ark/workspace-offline`.
