# Artifact Identity Hardening

## Objective

Move ResourceHandle and static-global evidence toward strict, reproducible provenance
without promoting public `ResourceHandle`, public `GObjects`, object identity, lookup,
mutation, return override, or runtime globals.

## Static Global Evidence

`scripts/build_static_global_promotion_evidence.py` now emits top-level
`artifact_identity` for `obelisk.static-global-promotion-evidence.v1`.

The identity hash is built from a canonical, path-redacted projection:

- schema;
- binary SHA256;
- static xrefs SHA256;
- copied/generated artifact hashes and provenance verification state;
- candidate kind/address and deterministic static-contract result;
- promotion blockers.

It intentionally excludes:

- `artifact_identity` itself;
- `generated_at_utc`;
- `obelisk_commit`;
- output paths, input paths, provenance sidecar paths, and command argv paths.

The offline artifact gate now requires complete static-global identity, safe IDs,
valid SHA256, and matching canonical hash. Consume mode still fails closed on bad
identity; promote mode remains blocked by static-only evidence and existing blockers.

## UObject Flag-Policy Evidence

`reconcile_gobjects_samples.py`, static-global evidence, and the UObject flag-policy
report now produce complete top-level identity:

```text
scripts/build_uobject_flag_policy_report.py
scripts/run_uobject_flag_policy_refresh.py
scripts/evaluate_resource_handle_revalidation.py
```

The policy-report identity hash is built from the path-redacted report projection:
schema/status gates, binary SHA, weak-helper summary, window artifact hashes and verified
provenance summaries, policy candidates, the internal revalidation contract, blockers,
non-claims, and redaction metadata. It excludes the identity hash itself, raw paths,
timestamps, raw disassembly snippets, raw helper/caller addresses, object indices,
serials, UE pointers, and lifecycle names.

`validate_offline_artifact_gate.py` now requires complete UObject flag-policy identity in
consume mode and verifies the canonical hash. `evaluate_resource_handle_revalidation.py`
counts a complete policy identity as a complete strict input; missing, partial, invalid,
or hash-mismatched identity keeps the internal UObject revalidation candidate rejected.
Public `ResourceHandle`, public GObjects, post-callback lookup, lifecycle names,
mutation, and return override remain blocked.

## Manifest Compatibility

Keep strict fail-closed compatibility for stale manifests. Do not infer identity from bare
hashes. Regenerate current static-global or UObject flag-policy manifests through the
current producers when a gate requires complete `artifact_identity`; older durable packs
remain historical evidence unless normalized. Normalization means a pack has a current
`artifact-pack.manifest.json` and matching relative `SHA256SUMS`; it proves container
integrity only and does not repair incomplete `artifact_identity`, promote candidate-only
evidence, or weaken per-schema consume/promote gates.

## Plugin Compatibility Direction

The lowest-risk ArkApi-familiar plugin categories remain:

```text
config/logging/lifecycle utilities
chat notification and plugin-local no-reply command parsing
read-only structure/inventory policy audit plugins
process-local timers for plugin housekeeping
```

Categories requiring player identity, permissions, replies, inventory mutation, object
lookup, return override, or raw UE access remain deferred until copied-data evidence,
privacy, lifecycle, and promotion gates exist.
