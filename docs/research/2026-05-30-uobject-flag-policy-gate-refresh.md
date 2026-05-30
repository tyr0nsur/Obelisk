# UObject Flag Policy Gate Refresh

## Context

Hilbert audited `/servidor/ark/workspace-offline` and identified the current
`uobject-flag-policy-static-negative` artifact as the most useful read-only blocker check
for ResourceHandle-related research. This note records the gate result so future rounds do
not repeat broad scans or treat the old artifact as consume-accepted.

## Command

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --manifest /servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/analysis/uobject-flag-policy-static-negative.redacted.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json
```

## Result

Status: `blocked`.

The artifact is useful historical input but does not satisfy the current consume gate.
Do not use it to promote `ResourceHandle`, public GObjects, object identity, lookup,
lifecycle validity, mutation, or return override claims.

## Blocking Reasons

- `weak_helper_caller_mode.direct_call_coverage` no longer matches the current contract.
- `weak_helper_caller_mode` is missing the required caller rows summary.
- Policy candidate support names use old labels such as
  `weak_helper_1d56c70_null_always` and `weak_helper_1d56c70_null_when_sil_zero` instead
  of the current expected labels.
- Every observed window is missing provenance.
- Required window patterns are missing or renamed. Examples include
  `gobjects_chunk_ref`, `gobjects_count_ref`, `null_return_branch`,
  `uobject_flags_load`, `strict_mode_guard`, `fuobjectitem_load`, `skip_branch`,
  `uobject_load`, `fuobjectitem_iteration`, and `set_0x100`.

## Next Action

Regenerate the flag-policy artifact with the current gate vocabulary and source
provenance sidecars before spending more effort on ResourceHandle promotion. This should be
done as focused offline artifact work, not as a broad core dump or live-server scan.

## Follow-up Triage

2026-05-30 supervised static/offline review selected UObject flag-policy regeneration as
the next highest-value offline research artifact after closing the Item return-only
preflight. The old artifact should stay historical. A regenerated policy report should be
built first under `/tmp` or another offline workspace from small static inputs with
verified provenance sidecars, then consumed with:

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --root <offline-root> \
  --manifest <offline-root>/uobject-flag-policy.redacted.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json
```

Expected near-term result: consume mode accepted, promote mode still blocked. This does
not promote `ResourceHandle`, public GObjects, post-callback lookup, lifecycle names,
mutation, return override, or any public SDK surface. Do not rerun broad
`scan_resource_handle_serials.py`, ReflectionScanner, ptrace/gcore, native exec probes,
server marker changes, or runtime observation for this refresh.

## 2026-05-30 Provenance Triage

The shortest refresh path is still viable with small existing inputs, but current disk
state cannot produce a consume-accepted artifact without inventing provenance. The raw
inputs below have useful evidence, yet lack verified sibling provenance sidecars with
matching `artifact_sha256` and `binary_sha256`.

Weak-helper caller-row inputs:

```text
/servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/raw/ghidra-headless.stdout
/servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/raw/r2-weak-helper-caller-modes.txt
/servidor/ark/workspace-offline/weak-helper-caller-mode-20260529T104655Z/raw/direct-call-counts.txt
```

UObject policy window inputs:

```text
/servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/raw/weak-helper-c70.objdump.txt
/servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/raw/gobjects-4000-skip.objdump.txt
/servidor/ark/workspace-offline/uobject-flag-policy-static-negative-20260529T143705Z/raw/gobjects-100-gc-pass.objdump.txt
```

Required sidecars before expecting consume acceptance:

```text
ghidra-headless.stdout.provenance.json
r2-weak-helper-caller-modes.txt.provenance.json
direct-call-counts.txt.provenance.json
weak-helper-c70.objdump.txt.provenance.json
gobjects-4000-skip.objdump.txt.provenance.json
gobjects-100-gc-pass.objdump.txt.provenance.json
```

The historical `weak-helper-provenance-bundle` does not clear this blocker because its
checked sidecars are not verified or do not correspond to the current converter inputs.
Next work should regenerate or verify sidecars from the original commands/tool versions,
then run the existing converter, policy builder, and offline artifact gate. Promote mode
must remain blocked with the candidate-only reason even after consume mode is accepted.
