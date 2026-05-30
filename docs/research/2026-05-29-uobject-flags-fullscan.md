# UObject Flags Fullscan

## Objective

Record the offline full-object-array scan for `UObject+0x8` masks `0x100` and `0x4000`
after the nonzero ResourceHandle revalidation pack.

## Environment

- Output pack: `/servidor/ark/workspace-offline/uobject-flags-fullscan-20260529T061305Z`
- Inputs: copied offline core artifacts under `/servidor/ark/workspace-offline`.
- Runtime posture: no live server, marker change, restart, ptrace, debugger, or scanner.
- Scope: offline `GObjects` traversal only, using `scripts/scan_resource_handle_serials.py`.

## Hypothesis

If complete copied-core scans find objects whose `UObject+0x8` flags include `0x100` or
`0x4000`, those samples can become negative/edge cases for classifying the weak-handle
helper's validity checks. If no such samples exist, the blocker remains semantic rather
than sample-volume based.

## Evidence

The full scans completed across both copied cores:

- `vanilla_full`: `828585` objects read, `2151` nonzero serial candidates, `0`
  `InternalIndex` mismatches, `0` `0x100`/`0x4000` flag samples.
- `second_source_full`: `975398` objects read, `2638` nonzero serial candidates, `0`
  `InternalIndex` mismatches, `0` `0x100`/`0x4000` flag samples.

The output JSON files are redacted summaries:

- `vanilla-full-serial-flags.redacted.json`
- `second-source-full-serial-flags.redacted.json`

## Result

Confirmed as an offline blocker refinement: the available copied cores do not provide
mask-positive `UObject+0x8` samples for `0x100` or `0x4000` across their full object-array
walks. This makes further broad core scanning a low-value next step for this blocker.
Later primary-core and post-RC artifacts supplied stronger internal `0x4000` candidate
accounting, strict reconciliation, and candidate-only serial policy. Treat this fullscan
as historical evidence that broad copied-core volume is not the blocker on the current
binary hash.

Not promoted: public `ResourceHandle`, post-callback object identity, lifetime/reuse
semantics, mutation, and return overrides remain blocked. The scan does not name the bits
or prove that matching `{index, serial}` pairs are safe after callbacks.

## Risks

- The scan can only classify objects present in the two copied cores. It does not prove the
  masks are absent in all runtime states.
- `core_sha256` was not passed into this run's redacted summaries; use the containing
  workspace identity and existing core evidence notes for artifact identity.
- No mask-positive samples means there is no runtime-derived truth table for these bits.

## Next Steps

- Use static/decompiler evidence around the weak-handle helper and version-matched UE4
  semantics to classify `UObject+0x8` checks.
- Do not repeat broad full scans for the current binary hash. The next useful evidence is
  an approved debug-runtime semantic pack with rejected object samples and serial
  reuse/wraparound observations; absent that live-ops brief, keep the lane no-scan.
- Keep the evaluator fail-closed with `post_callback_resource_handle_ready=false`.
