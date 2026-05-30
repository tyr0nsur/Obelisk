# Offline Artifact Packs

This runbook is for contributors who receive or prepare already-captured offline
evidence packs. It is limited to local file validation and comparison. Do not run server
operations, do not write into protected server trees, and do not describe raw binary or
dump locations in contributor notes.

## Scope

An artifact pack is a directory container with a normalized
`artifact-pack.manifest.json` and `SHA256SUMS`. The container can hold supported child
JSON manifests, reports, consume-gate outputs, comparison outputs, and other payload
files. The pack container is evidence packaging, not a promotion result.

Consume-mode acceptance means the pack is hygienic enough to cite as offline evidence for
the exact scope recorded by its child manifests. It does not promote public SDK APIs,
object identity, lookup, raw UE pointers, mutation, return overrides, runtime hooks, or
cross-binary portability.

## Required Pack Shape

- The pack root must be a real directory, not a symlink.
- Pack contents must be regular files or directories; symlinked entries fail closed.
- Root outputs must be named exactly `artifact-pack.manifest.json` and `SHA256SUMS`.
- Manifest schema must be `obelisk.artifact-pack.manifest.v1`.
- `artifact_id` must be a safe component, normally the pack directory name.
- `generated_utc` must be a real UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form.
- Every recorded file path must be pack-relative, not absolute, not empty, and not
  traversing upward.
- `SHA256SUMS` must include the current manifest hash plus every payload file hash.
- Child JSON with a supported schema is revalidated by the consume gate; unsupported JSON
  is only covered by the container checksum.

## Normalize And Check

Normalize once after the pack contents are final:

```sh
PACK=/path/to/offline-workspace/<pack-id>
python3 scripts/normalize_artifact_pack.py "$PACK" --json
```

If the pack id does not end in a timestamp, pass an explicit timestamp:

```sh
python3 scripts/normalize_artifact_pack.py "$PACK" \
  --artifact-id "<pack-id>" \
  --generated-utc "YYYY-MM-DDTHH:MM:SSZ" \
  --json
```

Before citing or handing off the pack, check it without rewriting files:

```sh
python3 scripts/normalize_artifact_pack.py "$PACK" --check --json
```

Check mode fails if any payload, manifest, or checksum file drifted after normalization.

## Consume Gate

Run the offline gate against the container manifest, not an arbitrary file in the pack:

```sh
OFFLINE_WORKSPACE=/path/to/offline-workspace
python3 scripts/validate_offline_artifact_gate.py \
  --root "$OFFLINE_WORKSPACE" \
  --manifest "$PACK/artifact-pack.manifest.json" \
  --mode consume \
  --json
```

The expected result for a usable pack is `status=accepted` with no blockers. If blockers
are present, keep the pack as rejected or fix the source artifact and normalize again.
Do not hide child-manifest blockers by citing only the container hash; the gate recurses
into supported child manifests and preserves their consume/promote blockers.

Promote mode is not a pack-container approval path. The gate intentionally blocks
artifact-pack manifests in promote mode as container-only evidence.

## Strict Target-Set Coverage

For redacted UFunction signature manifests that name target sets, run the consume gate
with strict coverage before treating the pack as current evidence:

```sh
python3 scripts/validate_offline_artifact_gate.py \
  --root "$OFFLINE_WORKSPACE" \
  --manifest "$PACK/artifact-pack.manifest.json" \
  --mode consume \
  --strict-target-set-coverage \
  --json
```

Strict coverage requires `target_set_coverage` to be complete and internally consistent:
declared target sets must be known, expected targets must match the project target-set
definition, emitted targets must match the signatures, and missing or unexpected targets
must be recorded as empty. Historical missing-coverage markers can allow old consume
checks, but strict mode still blocks them.

## Second-Source Compare

Reflection inventory packs need a distinct second source before they can support
second-source readiness claims. Compare the base and candidate packs:

```sh
BASE_PACK=/path/to/offline-workspace/<base-pack>
CANDIDATE_PACK=/path/to/offline-workspace/<candidate-pack>
python3 scripts/compare_reflection_inventory_packs.py \
  --base-pack "$BASE_PACK" \
  --candidate-pack "$CANDIDATE_PACK" \
  --fail-on-gaps \
  --json
```

The comparison accepts only candidate-only packs with matching binary SHA, distinct
artifact identity fields, complete FName-root summaries, no pack blockers, and no added,
removed, or changed redacted function rows. Its output is itself candidate-only evidence
and does not replace per-target readiness reports.

## Contributor Notes

When recording a pack in a PR, issue, or research note, include:

- pack id and `generated_utc`;
- `artifact-pack.manifest.json` SHA256 and `SHA256SUMS` SHA256;
- consume gate command shape and accepted/blocker status;
- whether strict target-set coverage was run;
- second-source comparison status when applicable;
- exact non-claims copied from the relevant child report or comparison.

Do not claim that a passing pack promotes a public SDK, raw UE access, object identity,
lookup, mutation, return overrides, ResourceHandle, or cross-binary support. A passing
pack is offline evidence for the stated target set and child manifest scope only.
