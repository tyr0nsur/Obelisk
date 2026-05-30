# Post-RC Contract Hardening Round

Date: 2026-05-30

## Context

This round reduced post-RC drift risk without expanding public API scope. The focus was
internal copied-data correctness for existing `GameplayPolicyEvent` backing and the next
internal item return-only candidate.

## Changes

- `StructureEventDispatcher` now rejects events whose scalar fields/types do not exactly
  match the public descriptor contract for each structure event kind.
- Structure observation activation now mirrors Inventory's cheap subscriber-aware dispatch
  predicate, so dispatch budget alone does not keep the hook hot path active when no
  structure subscribers exist.
- Item return-only gained a helper that builds the copied return observation and reserves
  budget as one operation, clearing output on rejected attempts or exhausted budget.
- Public SDK guardrails now check structure and inventory backing symmetrically: no
  structure identity, lookup, mutation, return override, or `ResourceHandle` claims.

## Validation

- `cmake --build build -j"$(nproc)"`
- `ctest --test-dir build --output-on-failure`
- `PYTHONPATH=scripts python3 -m unittest scripts.test_public_sdk_guardrails scripts.test_release_scope_guardrails scripts.test_research_doc_guardrails`
- `git diff --check`

## Non-Claims

This does not promote a public Items SDK, Inventory SDK, StructureEvents SDK,
`ResourceHandle`, object identity, lookup, mutation, return override, or live-server
behavior. Item return-only remains an internal/test-only candidate.
