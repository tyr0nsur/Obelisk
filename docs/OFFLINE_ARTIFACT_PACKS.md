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
- Legacy spellings such as `obelisk.artifact_pack.manifest.v1` are unsupported and fail
  closed as unknown schemas.
- `artifact_id` must be a safe component, normally the pack directory name.
- `generated_utc` must be a real UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form.
- Every recorded file path must be pack-relative, not absolute, not empty, and not
  traversing upward.
- `SHA256SUMS` must include the current manifest hash plus every payload file hash.
- Child JSON is always scanned for generic hygiene blockers such as protected-root
  strings and promotion overclaims. Child JSON with a supported schema is additionally
  revalidated by the consume gate; unknown `obelisk.*` schemas fail closed.
- Do not keep normalizer stdout files such as `normalize-artifact-pack.json` in the pack
  root. The normalizer treats them as payload; a zero-byte or stale JSON summary then
  blocks the consume gate as malformed or drifted child evidence.

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

## Optional Static Tooling

`radare2`, `rizin`, and Ghidra headless outputs may strengthen an offline evidence pack,
but they are not required to run pack normalization, consume gates, or repository tests.
Treat availability as an environmental fact: record `command -v`, version output when
available, exact commands, and the binary/artifact SHA only when the tool was actually
used.

Do not let optional-tool availability bypass path hygiene. Inputs, Ghidra project
directories, and radare/rizin/Ghidra text outputs must live under `/tmp`, an approved
offline workspace such as `<approved-offline-workspace>`, or another documented
non-protected artifact root. Direct or symlink-resolved reads from a protected server root
outside the approved offline workspace remain blockers, even if the tool is installed.
Existing analyzer text is reusable only when its provenance sidecar and child manifest
pass the same fail-closed consume gate as any other static artifact.
Relative path fields inside JSON manifests and provenance sidecars are resolved relative
to the JSON file that contains them before protected-root checks are applied; `../`
traversal into protected server trees remains a blocker even when the protected path is
not written literally.
CLI `--root` and hidden protected-root inputs may be absolute or relative; the gate
normalizes them before comparing direct path text and symlink-resolved paths.

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

Use `--manifest` for `artifact-pack.manifest.json`. Do not pass pack manifests through
`--artifact`; that path is for raw static artifacts with provenance sidecars and does not
recurse into or validate the pack container.

The expected result for a usable pack is `status=accepted` with no blockers. If blockers
are present, keep the pack as rejected or fix the source artifact and normalize again.
Do not hide child-manifest blockers by citing only the container hash; the gate recurses
into supported child manifests and preserves their consume/promote blockers.

Promote mode is not a pack-container approval path. The gate intentionally blocks
artifact-pack manifests in promote mode as container-only evidence.

## ResourceHandle Runtime Candidate Checks

Future ResourceHandle runtime artifacts are accepted only as internal planning inputs.
The gate recognizes these schemas in consume mode:

- `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1`
- `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1`

They must redact run identity, reference an accepted strict serial-policy source
artifact, expose only copied or aggregate reason/status fields, keep privacy flags false
for raw UE pointers, object indices, serial values, player/gameplay payloads, persistent
lookup tokens, protected paths, broad tracing, ReflectionScanner, ptrace/gcore, and
`FUObjectItem+0xc` serial claims, keep promotion/public readiness flags false, and use
only the schema's canonical top-level fields. Unknown top-level extension fields fail
closed because they are outside the output identity's canonical report. Promote mode
remains blocked. Passing these manifests does not approve a runtime observation window
and does not promote `ResourceHandle`, object identity, lookup, post-callback handles,
mutation, return override, GObjects, or public SDK surface.

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

## Build-Policy Gap Checks

To review known deferred build-policy blockers without a core, fixture root, or snapshot
pack, list the offline planning guidance first:

```sh
python3 scripts/compare_reflection_snapshots.py \
  --list-target-guidance \
  --target PrimalStructure.IsAllowedToBuild
```

Guidance filters use exact `Outer.Name` or `schema:Outer.Name` targets. An explicit
`--target` that does not match known deferred-target guidance fails closed instead of
returning an empty success report. A `--target-set` filter may return zero guidance
entries; that only means the set has no deferred-target guidance recorded here, not that
the set is promoted or that build-policy coverage exists.

Some target sets carry set-level planning guidance instead of per-target blocker
guidance. This is for offline evidence preparation only:

```sh
python3 scripts/compare_reflection_snapshots.py \
  --list-target-guidance \
  --target-set mission-copied-bool-policy-slice \
  --target-set transfer-baccept-only-policy-slice
```

Pass each target set at most once when listing guidance. Duplicate `--target-set`
filters fail closed instead of emitting repeated planning guidance.

The mission and transfer policy-slice guidance records the current non-promotion
boundaries: copied-bool evidence remains internal, distinct second-source layout is still
required for readiness claims, player/controller/object refs, arrays, payload identity,
and raw params stay redacted or recognition-only, and the output does not promote Mission
SDK, Transfer SDK, payload decoding, identity, lookup, mutation, return override, runtime
hooks, target-set expansion, or public API.

The JSON guidance for deferred build-policy targets includes `snapshot_prep_checks`.
Use those checks as an offline intake checklist when preparing a sanitized
`PrimalStructure.IsAllowedToBuild` snapshot: exact schema-qualified target naming,
distinct artifact identity, candidate-uobject membership for the target/property chain,
redaction or recognition-only handling for placement/player/context/raw params, and a
distinct sanitized second-source comparison before any readiness claim. These checks are
planning guidance only and do not add target-set coverage.

For deferred structure build-policy targets, contributors can check the current fixture
blocker without server paths:

```sh
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild \
  --target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild
```

The expected blocked state is `missing_base_snapshot` with candidate-only guidance. For
`PrimalStructure.IsAllowedToBuild` and `APrimalStructure.IsAllowedToBuild`, the report
also records why the target remains second-wave: no committed sanitized snapshot, no
distinct second-source layout, unproven placement-struct redaction policy, and blocked
build-denial/return-override policy. This guidance does not add target-set coverage or
promote `StructureEvents`, a build-policy SDK, identity, lookup, mutation, return
override, runtime hooks, or public API.

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
