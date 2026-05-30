# GObjects Cross-Manifest Comparison

## Objective

Record a lightweight comparison across existing `gobjects-sampling` manifests so future
rounds do not repeat broad GObjects scans when a smaller manifest check is enough.

## Inputs

- `inventory-action` manifest:
  `/servidor/ark/workspace-offline/inventory-action-compact-intake-second-source-20260529T121242Z/pack/gobjects-sampling/manifest.json`
- `minimal-refresh` manifest:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/pack/gobjects-sampling/manifest.json`
- `item-compact` manifest:
  `/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/pack/gobjects-sampling/manifest.json`

Generated comparison:

```text
/servidor/ark/workspace-offline/gobjects-cross-manifest-comparison-20260529T130344Z/report.json
schema=obelisk.gobjects-cross-manifest-comparison.v1
status=accepted_for_internal_offline_research
promotion_ready=false
```

## Result

The three manifests agree on the current binary-scoped GObjects candidate and static
evidence:

```text
binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
gobjects_candidate=0x595b7e0
sample_indices=[0, 1, 25447]
sample_25447.name=ServerChat
sample_25447.internal_index=25447
sample_25447.internal_index_match=true
static_xrefs_sha256=c54827854b8fd3a46715b9bda2c424eff9f42a5ef49a6941fa15b9d8029c6496
static_access_counts.load=13884
static_access_counts.store=11
static_access_counts.other=43
```

The manifests cover two distinct copied cores:

```text
inventory-action core=56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb
minimal-refresh core=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78
item-compact core=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78
```

Object counts differ across the independent process images, which is expected:

```text
inventory-action count=830438
minimal-refresh count=977251
item-compact count=977251
```

## Interpretation

This reinforces `0x595b7e0` as the right internal offline input for UFunction inventory and
target-set work on this ARK binary hash. It also reduces the value of repeating broad
FName/GObjects scans for the same binary/artifact family.

## Boundary

This is not a public promotion gate. It does not promote public GObjects, object identity,
lookup, `ResourceHandle`, lifecycle semantics, mutation, or return overrides. Current
ResourceHandle work remains blocked by `uobject_flags_validity_semantics_unproven`.

`obelisk.gobjects-cross-manifest-comparison.v1` is a local research/report schema, not an
offline artifact-gate allowlisted manifest schema. Do not cite this note as gate-accepted
promotion evidence.
