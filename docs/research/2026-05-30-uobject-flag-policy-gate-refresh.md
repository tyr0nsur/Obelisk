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
