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

## Next Strict-Identity Step

`reconcile_gobjects_samples.py` and static-global evidence now produce complete top-level
identity. The remaining direct ResourceHandle strict input is the UObject flag-policy
report:

```text
scripts/build_uobject_flag_policy_report.py
scripts/run_uobject_flag_policy_refresh.py
scripts/evaluate_resource_handle_revalidation.py
```

Strict mode should classify the UObject flag-policy report identity the same way it
classifies reconciliation and static-global inputs. Missing, partial, or invalid policy
identity must keep `promotion_ready=false`, `public_resource_handle_ready=false`, and
`post_callback_resource_handle_ready=false`.

## Compatibility Direction

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
