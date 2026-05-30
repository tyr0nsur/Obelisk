# GObjects Strict Consume Recapture Needed

Date: 2026-05-30

## Summary

The existing durable two-core GObjects manifest under `/servidor/ark/workspace-offline`
was produced before the current strict artifact-identity gate. It is useful historical
evidence, but it now fails consume validation with
`gobjects_two_core_manifest_missing_artifact_identity`.

A rebuilt strict manifest in `/tmp` passed consume validation and stayed promote-blocked,
which is the desired posture. No public GObjects promotion is implied.

## Current Evidence State

- Historical durable manifest:
  `/servidor/ark/workspace-offline/gobjects-two-core-manifest-20260529T091618Z/manifest.json`
- Current consume result for that manifest: blocked by missing artifact identity.
- Rebuilt strict manifest result in `/tmp`: consume accepted, promote blocked.
- Candidate globals from the accepted rebuild:
  - `gobjects_candidate=0x595b7e0`
  - `fname_root_slot=0x5956f30`
- Both sampled cores accepted `10/10` objects with `0` rejected samples.
- `public_gobjects_promotion_ready=false`

## Required Durable Recapture

When a current turn explicitly allows `/servidor/ark/workspace-offline` writes, rebuild
the strict consume manifest from the existing reports instead of treating the pre-strict
manifest as current evidence:

```bash
python3 scripts/build_gobjects_two_core_manifest.py \
  --binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --report primary=/servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/core-reconciliation/gobjects-reconciliation.json \
  --report second=/servidor/ark/workspace-offline/gobjects-two-core-crosscheck-20260529T090844Z/second-core-10-sample-gobjects-reconciliation.json \
  --capture-id gobjects-two-core-20260529T091618Z \
  --evidence-pack-id gobjects-two-core-strict-consume-pack \
  --output /servidor/ark/workspace-offline/gobjects-two-core-strict-consume-20260530T000000Z/manifest.json
```

Then validate it in consume mode:

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline \
  --manifest /servidor/ark/workspace-offline/gobjects-two-core-strict-consume-20260530T000000Z/manifest.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json
```

## Non-Claims

- This is strict consume-only internal evidence.
- This does not promote public GObjects, ResourceHandle, lookup, identity, mutation, return
  overrides, or raw UE object access.
- This does not require attaching to a live ARK process.
