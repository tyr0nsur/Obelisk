# FName Index Manifest Plan

## Objective

Define the minimal production-safe path from raw `FName` indices to a binary-scoped
manifest/resolver contract. The goal is to keep the first stable Obelisk line useful for
filtered `ProcessEvent` observation without making observed ARK indices look portable
across binaries or clusters.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-28
- Current ARK binary SHA256 used by committed evidence:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Server posture: offline planning only. No server restart, marker edit, ptrace/gcore,
  ReflectionScanner, runtime probe, or `/servidor/ark` write was performed.

## Current Problem

The stable interaction boundary is intentionally narrow: plugins can register filtered
callbacks by exact `FName` index. That is safe for the hot `ProcessEvent` path, but it is
not ergonomic or portable enough for future mod authors.

Current example config in `oBaseEvents` uses:

```json
"process_event": {
  "enabled": false,
  "filtered_function_index": -1,
  "log_limit": 5
}
```

That field must remain a low-level escape hatch, not the long-term SDK pattern. Raw
indices such as `9619 -> ServerChat` are binary evidence, not stable public names.

## Minimal Manifest Shape

Use a repo or operator-provided JSON manifest keyed by ARK binary SHA256:

```json
{
  "schema": "obelisk.fname-index-manifest.v1",
  "ark_binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
  "source": "offline_core",
  "evidence_status": "candidate-only",
  "promotion_evidence": null,
  "names": [
    {
      "name": "ServerChat",
      "index": 9619,
      "number": 0,
      "evidence": "docs/research/2026-05-27-arkserver-core-fname-evidence.md"
    }
  ]
}
```

Validation rules:

- `schema` must equal `obelisk.fname-index-manifest.v1`.
- `ark_binary_sha256` must be strict lowercase SHA256 hex and must match the running or
  target `ShooterGameServer` hash before any entry is used.
- `name` must be an exact FName string, not a substring.
- `index` must be non-negative and unique per manifest.
- `index` and `number` must fit the runtime `int32_t` ABI and JSON booleans are invalid.
- `number` values other than `0` are rejected until runtime filters can distinguish full
  `FName` identity instead of only `ComparisonIndex`.
- `evidence_status` controls use:
  - `candidate-only`: tooling and explicit operator/debug configs only;
  - `accepted`: allowed for stable filtered callback config generation after second-source
    evidence.
- `accepted` manifests must include `promotion_evidence` with schema
  `obelisk.fname-index-promotion-evidence.v1`, `status=accepted`,
  `second_source=true`, and a dated `docs/research/YYYY-MM-DD-*.md` report path.
- Each accepted entry must point to a dated `docs/research/YYYY-MM-DD-*.md` note or an
  evidence-pack `manifest.json` path. Loose strings such as `a.md` or undated research
  notes are rejected for accepted manifests.

## Acceptance Criteria For `accepted`

Do not flip a manifest from `candidate-only` to `accepted` just because the validator can
parse it or because a single core scan resolves the expected names. Promotion requires a
dated research report with:

- the exact ARK binary SHA256 and the manifest SHA256;
- distinct artifact identity for the primary and second source: `artifact_kind`,
  `artifact_sha256`, `capture_id`, and `evidence_pack_id`;
- the commands used to produce and validate both sources;
- exact resolved rows for each promoted FName, including `name`, `index`, `number`, and
  evidence path;
- reject conditions checked: hash mismatch, missing name, duplicate index, duplicate
  identity, non-zero `number`, reused primary-core FName root, and stale candidate-only
  config generation;
- an explicit conclusion that the promotion is name/index evidence only and does not
  promote parameter layouts, gameplay mutation, or public SDK callback-by-name APIs.

An independent static path may support promotion only when it explains the name table/root
candidate with reproducible readelf/objdump or decompiler evidence and is combined with a
distinct artifact or a documented reason why the static evidence is independent. Static
evidence alone must not turn `promotion_gate.ready` true for UE4 globals or module layouts.

Per-entry evidence-pack manifest paths may be absolute offline artifact paths or
repo-relative paths, but they must end in `manifest.json`, must not contain `..`, and must
not point under `/servidor/ark`. The top-level `promotion_evidence.report` must remain a
repo-relative dated `docs/research/YYYY-MM-DD-*.md` note so future reviewers can review the
promotion decision without local artifact access.

Final accepted-manifest validation should include a stable-config check such as:

```bash
python3 scripts/validate_fname_index_manifest.py \
  --manifest <accepted-manifest.json> \
  --ark-binary-sha256 <lowercase-sha256> \
  --require-accepted \
  --resolve-name <ExactFName> \
  --json
```

## Resolver Direction

First implementation should be offline/operator-side, not a new hot-path runtime lookup:

1. Add a validator/lookup script that loads a manifest, verifies `ark_binary_sha256`, and
   resolves exact names to indices. Name resolution rejects `candidate-only` manifests by
   default; `--allow-candidate` is reserved for explicit internal/debug use.
2. Let plugin examples keep `filtered_function_index` as the runtime field, but document
   a generated-config workflow that resolves `process_event.function_name` to
   `filtered_function_index` before deployment.
   Generated config notes should include `generated_for_ark_binary_sha256` for operator
   review in clustered deployments. Non-JSON resolver output must print that field next
   to the resolved index so manual config generation does not lose the binary binding.
3. Do not expose a public plugin ABI callback-by-name until runtime FName resolution,
   lifetime, and binary mismatch behavior are accepted.
4. In a later ABI/API round, append name-based registration only after the resolver can
   fail closed by binary hash and exact FName identity.

## Risks

- A manifest can become stale after an ARK binary update. Hash mismatch must fail closed.
- Manifest acceptance can be confused with layout promotion. FName name/index evidence does
  not prove parameter layout or safe gameplay mutation.
- Clustered servers may share plugin configs but run different binaries during updates.
  Generated configs must record the binary hash they were generated for.
- Runtime callback-by-name would add work to the hot path unless names are resolved once
  at load time and callbacks remain index-filtered internally.

## Next Steps

1. `scripts/scan_core_fname_tables.py` can emit a candidate-only manifest directly from an
   offline core scan:

```bash
python3 scripts/scan_core_fname_tables.py \
  --core <core> \
  --ark-binary-sha256 <lowercase-sha256> \
  --manifest-out <pack-dir>/core.fname-index-manifest.json \
  --manifest-evidence <pack-dir>/manifest.json \
  --json > <pack-dir>/core.fname-table-scan.json
```

The scanner writes only `candidate-only` manifests. It exports exact rows where both
`header_index_ok` and `name_matches_label` are true, skips the sentinel `None` entry,
requires a lowercase binary SHA, and fails closed when no exact names or multiple
manifest-ready candidates exist.

2. `scripts/build_core_dump_evidence_pack.py --scan-fname-tables` wires that candidate
   manifest into the evidence pack as `artifacts.core_fname_index_manifest` and records
   `fname_table_scan.candidate_manifest_status`, `requested_indices`,
   `manifest_readiness`, and `candidate_manifest` from the scan output. The evidence-pack
   `promotion_gate.ready` remains false.
3. Use `scripts/validate_fname_index_manifest.py` with `--manifest`, either
   `--ark-binary <ShooterGameServer>` or `--ark-binary-sha256 <sha256>`,
   and `--resolve-name <Name>` for offline
   operator-side config generation. `--resolve-name` must always include an expected
   binary hash, preferably computed from an offline binary path, so stale manifests fail
   closed. `--ark-binary` paths under `/servidor/ark`, including symlinked live-server
   paths, are rejected so config preparation uses offline binary copies or explicit SHA256
   inputs. Candidate-only manifests must use `--allow-candidate` explicitly and remain out
   of the stable config workflow by default.
4. Keep fixtures under `tests/fixtures/fname_index_manifests/` candidate-only until
   second-source evidence is accepted.
5. Keep tests covering accepted, default candidate rejection, explicit candidate override,
   duplicate index, duplicate identity, hash mismatch, strict lowercase hashes, accepted
   evidence paths, missing evidence, and missing-name cases.
6. Update `docs/oBaseEvents.md` with an operator-side name-to-index workflow once the
   validator exists.
7. Keep public ABI unchanged until the manifest/resolver path is validated and
   second-source FName evidence exists.
