# Aggregate/Census Product Priority

Date: 2026-05-31

## Objective

Audit the Product/SDK boundary for Structure, Dino, and Buff aggregate/census planning in
`docs/PLUGIN_HUB_CAPABILITY_MATRIX.md` and
`docs/research/2026-05-31-v02-module-priority.md`.

This note is a product-direction recommendation only. It does not promote a public SDK,
runtime observer, callback family, descriptor, capability bit, ABI contract, object
identity, lookup API, mutation path, enforcement path, return override, or ArkApi/AseApi
compatibility target.

## Boundary Findings

- Blocker: no Structure, Dino, or Buff aggregate/census lane has a promoted public SDK
  surface, runtime-observation approval, public callback ABI, descriptor/resource kind,
  installed SDK consumer coverage, or promotion gate.
- Debt: the capability matrix names Structure census/proximity planning explicitly, while
  Dino and Buff aggregate/census are only discussed in the v0.2 priority note as possible
  future product directions. If Dino or Buff aggregate/census stays in product planning,
  add matrix rows later with the same planning-only/no-runtime boundary.
- Clear: both audited documents avoid claiming current SDK availability or runtime
  permission for aggregate/census work. The v0.2 note frames Structure/Dino/Buff
  aggregate/census as future Plugin Hub value only if it remains aggregate,
  privacy-preserving, copied-data only, and separately promoted.

## Recommendation

Advance Structure aggregate/census as the leading product-facing planning direction, but
only as a planning lane. It has the clearest safe product shape because counts by copied
category and bounded proximity signals can be designed without public structure handles,
exact coordinates, ownership lookup, linked-structure traversal, mutation, or cross-event
identity.

Defer Dino aggregate/census as a product lane. Keep near-term Dino work focused on compact
recognizer and scalar redaction hardening. A product-facing aggregate/census lane still
needs a separate copied payload proposal that avoids dino/player identity, classification
leakage, interaction authority, spawn/cosmetic mutation, carry-rule enforcement, and
runtime promises.

Defer Buff aggregate/census as a product lane. Keep Buff work as offline recognizer,
fixture, and redaction hardening until class/object semantics and aggregate value are
clearer. A future Buff census proposal must avoid actor/player identity, buff instance
handles, gameplay authority, mutation, duration/state disclosure beyond approved
aggregates, and runtime promises.

## Required No-Claims

Any future mention of Structure, Dino, or Buff aggregate/census should explicitly avoid
claiming:

- public SDK, Plugin Hub module, callback, descriptor, resource kind, or capability-bit
  readiness;
- runtime observer approval, server window approval, ProcessEvent tracing approval, or
  release readiness;
- public GObjects traversal, UE pointer access, object handles, exact coordinates,
  ownership lookup, player/dino/structure/buff identity, or cross-event correlation;
- mutation, enforcement, denial, spawn/cosmetic changes, buff state changes, return
  override, commands, permissions, economy, persistence, RCON, webhooks, or ArkApi/AseApi
  compatibility.

## Validation

This pass read only the requested workflow skill and the two audited documents, then wrote
this recommendation note. It did not use Git, push/tag, Discord, server paths, runtime
probes, scanners, ptrace, or `gcore`.
