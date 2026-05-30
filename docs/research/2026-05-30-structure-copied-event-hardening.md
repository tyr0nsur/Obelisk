# Structure Copied Event Hardening

Date: 2026-05-30

## Context

Structure copied-event dispatch was aligned with the safer Inventory copied-event pattern.
The goal is internal runtime hardening only: no public StructureEvents SDK, no object
identity, no lookup, no mutation, and no return override.

## Changes

- Structure dispatch observation now requires a live subscriber before consuming dispatch
  budget.
- `StructureEventDispatcher` keeps an atomic subscriber mirror for the hook fast path,
  while lifecycle cleanup remains owned by the dispatcher lock/deferred-destroy state.
- Matched structure invocations can now build and reserve a self-contained
  `CopiedStructureEvent` once, then dispatch that reserved copy after the original
  `ProcessEvent` returns.
- `CopiedStructureEvent` copy/move operations rebind scalar spans to owned storage.
- Scalar copy rejects mismatched exposed range sizes instead of trusting borrowed ranges.
- Structure recognition contains reader exceptions and fails closed as implausible input.

## Validation

- `cmake --build build --target process_event_structure_reflection_tests structure_event_dispatcher_tests obelisk -j"$(nproc)"`
- `ctest --test-dir build --output-on-failure -R '^(ProcessEventStructureReflectionTests|StructureEventDispatcherTests)$'`
- `PYTHONPATH=scripts python3 -m unittest scripts.test_public_sdk_guardrails scripts.test_release_scope_guardrails scripts.test_research_doc_guardrails`
- `cmake --build build -j"$(nproc)"`
- `git diff --check`

## Non-Claims

This does not promote a public StructureEvents SDK, structure identity, `ResourceHandle`,
UE pointer exposure, return overrides, or live-server behavior. It only hardens the
internal copied-scalar route used by promoted policy events and future gated bridges.
