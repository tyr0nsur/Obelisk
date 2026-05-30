# UObject Flag Policy Gate Refresh

## Context

A read-only static/offline audit of `/servidor/ark/workspace-offline` identified the
current `uobject-flag-policy-static-negative` artifact as the most useful blocker check
for ResourceHandle-related research. This note records the gate result so future rounds
do not repeat broad scans or treat the old artifact as consume-accepted.

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

The canonical repo-side orchestration command is now
`scripts/run_uobject_flag_policy_refresh.py`. It expects an input root with `weak/` and
`windows/` subdirectories, requires rich provenance sidecars, writes generated redacted
outputs under a caller-provided output root outside Git, requires consume mode to accept,
and requires promote mode to stay blocked with the candidate-only blocker. The driver
rejects input roots under protected live-server paths except the approved offline
workspace and rejects outputs inside Git or protected live-server paths.

## Durable Rich-Provenance Refresh

The `/tmp` rehearsal inputs were preserved under:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z
```

The canonical driver then produced a durable refresh under:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z
```

Result:

- `scripts/run_uobject_flag_policy_refresh.py` returned
  `status=accepted_internal_static_evidence`.
- Consume gate accepted
  `uobject-flag-policy.redacted.json`
  (`sha256=836723c1c88314a5d8c52b3a67b0dcac455708e4fc577d449740c2a6ba33d758`).
- Promote gate stayed blocked with
  `promote_mode_uobject_flag_policy_candidate_only` and
  `promote_mode_manifest_has_non_claims`.

This closes the stale-artifact refresh blocker for internal ResourceHandle research only.
It still does not promote `ResourceHandle`, public GObjects, object identity, lookup,
lifecycle names, mutation, return override, or any public SDK surface.

For future durable refreshes, prefer `scripts/run_uobject_flag_policy_refresh.py` rather
than calling only the offline artifact gate. The direct consume gate accepts candidate
reports with minimal verified sidecars for mechanical indexing, while the driver requires
the richer preflight (`command`, `tool`, `tool_version`, `source_path`, and address ranges)
that makes this refresh reproducible enough for ongoing ResourceHandle research.

## Durable Pack Manifest

The durable refresh now includes a pack manifest and checksums in the artifact root:

```text
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/artifact-pack.manifest.json
/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/SHA256SUMS
```

Pack hashes:

- `artifact-pack.manifest.json`:
  `1f678c05461131055e4b18fd68862de431a27bbf49609297030ac62bf6f5478d`
- `SHA256SUMS`:
  `cf76ee33a8ea640233af7eff4de78171254a5ee5fa11de714259b27f2731a87a`
- `uobject-flag-policy.redacted.json`:
  `836723c1c88314a5d8c52b3a67b0dcac455708e4fc577d449740c2a6ba33d758`
- `weak-helper-caller-mode.redacted.json`:
  `4513dc8d7a78ced360748cffb92004c8dee152bb48e6d1be5045b00b39c9a486`
- `rich-provenance-preflight.json`:
  `122df02aac82f0d72fb5440b81e7dab1fc1dac6bda67054cd52cb6b2ff4fe9d8`
- `uobject-flag-policy.consume-gate.json`:
  `026122e801317b5a3b8761480d4f47fde99dcacbf7c80a117546bf9f87ff668e`
- `uobject-flag-policy.promote-gate.json`:
  `d57dcd2c6f8b83c8cf70bc392fb812d32d051f251c846d98c24ca74476fddab8`

The manifest keeps `promotion_ready=false`, `public_resource_handle_ready=false`, and
`post_callback_resource_handle_ready=false`. Treat this pack as canonical internal
static evidence for the current binary hash, not as a public ResourceHandle, GObjects,
identity, lookup, lifecycle, mutation, return-override, or SDK promotion.

## Gate Contract Hardening

Follow-up audit found that consume mode already required the
`internal_revalidation_contract`, but it did not fully reject contradictions in adjacent
fields. The gate now also validates the exact `weak_helper_caller_mode` shape, requires
`promotion_gate_ready=false`, requires the expected `0x100` / `0x4000` flag rules, rejects
unexpected fields in `policy_candidates`, and scans extra `remaining_blockers` /
`non_claims` entries for public `ResourceHandle`, lookup, SDK, runtime, or callback
overclaims.

This is a validator hardening only. It does not change the durable artifact's promotion
status and does not promote `ResourceHandle`, public GObjects, object identity, lookup,
lifecycle names, mutation, return override, or any public SDK surface.
