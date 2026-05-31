# Dispatcher Hot-Path Benchmark Priority

Date: 2026-05-31

## Finding

Structure and Inventory copied-event dispatchers sit on ProcessEvent-adjacent hot paths,
but their current documentation does not record a dedicated allocation benchmark target.
Both lanes already rely on cheap subscriber-aware activation and strict copied-data
guardrails, yet allocation behavior still needs an explicit regression signal before more
runtime copied-event producers are added.

The immediate gap is dispatcher snapshot allocation coverage for:

- disabled lanes;
- closed gates;
- zero dispatch budget;
- no-subscriber dispatch;
- nonmatching FNames;
- up to four subscribers using stack-backed snapshots;
- five subscribers using the heap fallback path.

Mission copied-bool now has a local dispatcher perf guard for the invalid,
no-subscriber, four-subscriber stack, and five-subscriber heap cases. Treat that as a
benchmark shape reference only. Mission remains test-only and unwired from runtime, and it
does not authorize Structure or Inventory API promotion.

## Objective

Add focused hot-path benchmark coverage before expanding Structure or Inventory runtime
copied-event production. The benchmark should report allocation counts for no-subscriber
and subscriber snapshot paths, and should fail closed on regressions that would allocate
on the disabled, gate-closed, zero-budget, no-subscriber, or nonmatching-FName paths.

This is a performance guardrail objective, not a product/API milestone.

## Non-Claims

This note does not promote public `StructureEvents`, public Inventory or Items SDKs,
public dispatcher APIs, new ABI fields, descriptors, runtime gates, hook wiring,
identity, lookup, mutation, return override, ResourceHandle, live-server validation, or
server observation. Any future public surface still needs copied-data ownership,
capability and `struct_size` gates, privacy review, lifecycle cleanup, second-source/static
evidence, and the normal release guardrails.
