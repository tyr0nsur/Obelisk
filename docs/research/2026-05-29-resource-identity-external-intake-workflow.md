# Resource Identity External Artifact Intake Workflow

## Objective

Define the safest next evidence-pack workflow for resource identity when the ARK core and
matching `ShooterGameServer` binary are provided as copied artifacts outside
`/servidor/ark`. This workflow is offline only. It does not authorize server access,
`ptrace`, `gcore`, live attach, marker changes, ReflectionScanner, native exec probes, or
runtime observation.

The goal is a focused `GObjects` / `FUObjectItem` identity evidence pack for internal
research. Passing this workflow does not expose Resource handles, promote a public ABI, or
prove cross-restart identity.

## Offline Workspace

Use `/servidor/ark/workspace-offline` or another approved offline workspace:

```bash
export OBI_INCOMING=/path/to/external/drop
export OBI_CASE=resource-identity-$(date -u +%Y%m%dT%H%M%SZ)
export OBI_WORK=/servidor/ark/workspace-offline/$OBI_CASE
export OBI_BIN_SRC="$OBI_INCOMING/ShooterGameServer"
export OBI_CORE_SRC="$OBI_INCOMING/core"

mkdir -p "$OBI_WORK/raw" "$OBI_WORK/intake"
```

Before copying, reject any source or destination that resolves under `/servidor/ark`:

```bash
for p in "$OBI_BIN_SRC" "$OBI_CORE_SRC" "$OBI_WORK"; do
  rp=$(realpath -m "$p")
  case "$rp" in
    /servidor/ark|/servidor/ark/*) echo "reject live-server path: $rp" >&2; exit 1 ;;
  esac
done
```

Copy the externally provided artifacts into the offline workspace and record hashes:

```bash
cp -av --reflink=never -- "$OBI_BIN_SRC" "$OBI_WORK/raw/ShooterGameServer"
cp -av --reflink=never -- "$OBI_CORE_SRC" "$OBI_WORK/raw/core"

sha256sum "$OBI_WORK/raw/ShooterGameServer" "$OBI_WORK/raw/core" \
  | tee "$OBI_WORK/raw/SHA256SUMS"
file "$OBI_WORK/raw/ShooterGameServer" "$OBI_WORK/raw/core" \
  | tee "$OBI_WORK/raw/file.txt"
readelf -h -W "$OBI_WORK/raw/ShooterGameServer" \
  | tee "$OBI_WORK/raw/readelf-header.txt"
```

If the provider supplied checksums, verify them against the copied files before intake:

```bash
(cd "$OBI_WORK/raw" && sha256sum -c /path/to/provider/SHA256SUMS)
```

## Scan-Only Plan

Generate a reviewable scan-only plan first. This command only plans the FName-table scan;
it must not include `--gobjects-candidate` or full-intake arguments.

```bash
cd /home/flowcommunity-ark/Obelisk
python3 scripts/run_second_source_core_intake.py \
  --binary "$OBI_WORK/raw/ShooterGameServer" \
  --core "$OBI_WORK/raw/core" \
  --pack-dir "$OBI_WORK/intake" \
  --scan-only \
  --json-plan \
  | tee "$OBI_WORK/intake/scan-only-plan.json"
```

After the plan is reviewed and all paths resolve under the approved offline workspace,
execute only the offline scan phase:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary "$OBI_WORK/raw/ShooterGameServer" \
  --core "$OBI_WORK/raw/core" \
  --pack-dir "$OBI_WORK/intake" \
  --scan-only \
  --execute \
  | tee "$OBI_WORK/intake/scan-only-execute.txt"
```

Review `$OBI_WORK/intake/fname-scan/manifest.json`,
`$OBI_WORK/intake/fname-scan/core.fname-table-scan.json`, and any generated
`core.fname-index-manifest.json`. A scan hit is candidate-only; it is not accepted FName
evidence and not GObjects promotion.

## Reviewed GObjects Sampling Plan

Only after the artifact-specific FName root is reviewed, plan the resource-identity
sampling pack. For the current ARK binary hash, the known research candidate remains
`GObjects=0x595b7e0`; the FName root slot must come from this artifact's scan, not from a
primary-core default.

```bash
export OBI_VERIFIED_FNAME_ROOT_SLOT=0x5956f30
export OBI_GOBJECTS=0x595b7e0

python3 scripts/run_second_source_core_intake.py \
  --binary "$OBI_WORK/raw/ShooterGameServer" \
  --core "$OBI_WORK/raw/core" \
  --pack-dir "$OBI_WORK/intake" \
  --snapshot-root "$OBI_WORK/candidate-ufunction-snapshots" \
  --verified-fname-root-slot "$OBI_VERIFIED_FNAME_ROOT_SLOT" \
  --gobjects-candidate "$OBI_GOBJECTS" \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447 \
  --target-set minimal-second-source-intake \
  --json-plan \
  | tee "$OBI_WORK/intake/full-intake-plan.json"
```

Full execution remains a separate review gate:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary "$OBI_WORK/raw/ShooterGameServer" \
  --core "$OBI_WORK/raw/core" \
  --pack-dir "$OBI_WORK/intake" \
  --snapshot-root "$OBI_WORK/candidate-ufunction-snapshots" \
  --verified-fname-root-slot "$OBI_VERIFIED_FNAME_ROOT_SLOT" \
  --gobjects-candidate "$OBI_GOBJECTS" \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447 \
  --target-set minimal-second-source-intake \
  --execute \
  | tee "$OBI_WORK/intake/full-intake-execute.txt"
```

For resource identity, review only whether sampled objects round-trip through
`InternalIndex`, class and outer pointers are plausible object-array members, and both
`FUObjectItem+0x8` and `FUObjectItem+0xc` are recorded without assuming `+0xc` is the
serial. Current static evidence favors the `+0x8` serial-backed hypothesis while `+0xc`
remains unknown.

## Validation Gates

- All input, output, and manifest paths resolve under `/servidor/ark/workspace-offline` or
  another approved offline root, never directly under `/servidor/ark/obelisk/dumps`.
- The copied binary and core hashes are recorded before any scan.
- Provider checksums, if present, match the copied artifacts.
- The binary hash matches the expected ARK binary for the candidate under review.
- The core hash, capture id, and evidence pack id are distinct from the primary core.
- `scan-only` output is treated as candidate-only and is not used for promotion.
- Full intake uses an artifact-specific FName root slot reviewed from this core.
- `manifest.json` reports complete evidence; `partial-gdb-failed` and
  `gdb_core_failed=true` are blockers.
- Snapshot comparison, if run, must report
  `schema=obelisk.reflection-snapshot-readiness.v1`,
  `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, no blockers, and the
  intended target set.

## Blockers

- Any path resolves under `/servidor/ark`.
- The external artifacts are missing, malformed, symlinked into a live-server tree, or
  lack verifiable hashes.
- The binary hash does not match the candidate's recorded ARK binary hash.
- The core is a renamed copy of the primary fixture by SHA256, capture id, or evidence
  pack id.
- The FName root is reused from another core instead of verified from this artifact.
- GDB core inspection fails, or `--allow-partial-gdb` is required.
- `GObjects` samples do not round-trip by `InternalIndex`, or class/outer membership is
  inconsistent.
- `FUObjectItem` serial/metadata remains ambiguous for invalidation semantics.
- Any proposed result requires live server access, runtime probes, or public ABI exposure.
