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

Follow-up audit found a complete hash-matched sidecar set under
`/tmp/obelisk-uobject-flag-policy-refresh-check`, but those sidecars are minimal. They
prove `verified=true`, the expected binary hash, and artifact hash equality only; they do
not record command lines, source paths, start/stop ranges, or tool versions. Treat them as
mechanical consume-gate material, not as full reproducible provenance.

Tool versions observed in surrounding logs/manifests are Ghidra 12.1 PUBLIC, OpenJDK
21.0.10, radare2 5.5.0, and GNU objdump/binutils 2.42. Of the six required inputs, only
the `gobjects-4000-skip` window currently has a located richer sidecar with objdump
command and start/stop range. A production-quality refresh should regenerate or enrich the
other five inputs with command/range/tool provenance before treating the artifact as
durable evidence for future `ResourceHandle` work.

Before running the converter/builder path, use the repo-local preflight below to check that
all required inputs have verified sidecars. The command is read-only and should block when
sidecars are missing, unverifiable, hash-mismatched, or path-tainted:

```bash
python3 scripts/validate_uobject_flag_policy_provenance_inputs.py \
  --root <offline-root> \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --ghidra-stdout <offline-root>/weak/ghidra-headless.stdout \
  --r2-windows <offline-root>/weak/r2-weak-helper-caller-modes.txt \
  --direct-call-counts <offline-root>/weak/direct-call-counts.txt \
  --window weak_helper_reject_0x100=<offline-root>/windows/weak-helper-c70.objdump.txt \
  --window strict_0x4000_behavior=<offline-root>/windows/weak-helper-c70.objdump.txt \
  --window gobjects_backed_0x4000_skip=<offline-root>/windows/gobjects-4000-skip.objdump.txt \
  --window gc_static_0x100_support=<offline-root>/windows/gobjects-100-gc-pass.objdump.txt \
  --json
```

Use `--require-rich-provenance` only when the source sidecars already carry mechanical
reproduction metadata. That opt-in layer requires `command`, `tool`, `tool_version`,
`start_address`, `stop_address`, and `source_path`, and validates command/path hygiene plus
monotonic address ranges. Do not add placeholder fields just to satisfy the preflight;
minimal verified sidecars remain valid for the default route.

Follow-up `/tmp` rehearsal confirmed the rich route is mechanically viable against the
offline ShooterGameServer binary
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`. Regenerating the six
small raw inputs with Ghidra 12.1, radare2 5.5.0, and GNU objdump 2.42 plus rich sidecars
made `validate_uobject_flag_policy_provenance_inputs.py --require-rich-provenance`
accepted, the consume gate accepted, and promote mode blocked with the expected
candidate-only blockers. Keep this as internal static evidence only; it does not promote
`ResourceHandle`, object identity, lookup, lifecycle names, mutation, or return override.
