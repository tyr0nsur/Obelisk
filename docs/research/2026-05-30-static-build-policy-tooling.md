# Static Build-Policy Offline Tooling Audit

Date: 2026-05-30
Obelisk commit: 9913132

## Objective

Audit currently available offline, non-protected tooling and artifacts that can support
`IsAllowedToBuild` and static build-policy research. This pass did not use server
instances, did not read or write `/servidor/ark`, and did not promote any candidate.

## Commands

- `git -C /home/flowcommunity-ark/Obelisk rev-parse --short HEAD`
- `git -C /home/flowcommunity-ark/Obelisk status --short`
- `command -v radare2`
- `radare2 -v`
- `command -v analyzeHeadless`
- `analyzeHeadless 2>&1 | head -40`
- `analyzeHeadless -version 2>&1 | head -20`
- `java -version 2>&1 | head -3`
- `readlink -f /usr/local/bin/analyzeHeadless`
- `find /home/flowcommunity-ark/obelisk-artifacts ...`
- `readlink -f` path hygiene scan for artifacts under `/home/flowcommunity-ark/obelisk-artifacts`
- `sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- `file /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`

## Tooling

- `radare2`: `/usr/bin/radare2`, version `5.5.0`.
- `analyzeHeadless`: `/usr/local/bin/analyzeHeadless`, resolves to
  `/opt/ghidra/ghidra_12.1_PUBLIC/support/analyzeHeadless`.
- Java used by Ghidra headless: OpenJDK `21.0.10`.

## Offline Artifact Availability

Root: `/home/flowcommunity-ark/obelisk-artifacts`

Inventory count from the offline root:

- Files: 272
- Directories: 62
- Symlinks: 1

Path hygiene result:

- No listed artifact path resolved to `/servidor/ark`.
- No listed artifact path resolved to `/servidor/ark/workspace-offline`.
- The only symlink is
  `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/bin/ShooterGameServer`,
  pointing to the offline binary path under `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/...`.

Offline binary:

- `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- SHA256: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- File type: ELF 64-bit LSB x86-64 executable, dynamically linked, stripped.

Static-global baseline artifacts:

- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump.provenance.json`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt.provenance.json`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt.provenance.json`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-xrefs.json`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-evidence.json`
- `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json`

Build-policy and structure-related artifacts:

- `/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.json`
- `/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.consume-gate.json`
- `/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.promote-gate.json`
- `/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.json`
- `/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.consume-gate.json`
- `/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.promote-gate.json`
- `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z/item-return-only-policy-slice.json`
- `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-second-source-20260530T084918Z/item-return-only-policy-slice.json`
- `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-second-source-20260530T084918Z/item-return-only-second-source-readiness.json`
- `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-bool-tail-refresh-20260530T172552Z/compare-readiness.json`

Adjacent static-policy artifacts that may help blocker accounting but are not
`IsAllowedToBuild` promotions by themselves:

- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/uobject-flag-policy.redacted.json`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/rich-provenance-preflight.json`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/weak/r2-weak-helper-caller-modes.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/weak/ghidra-headless.stdout`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/windows/gobjects-100-gc-pass.objdump.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/windows/gobjects-4000-skip.objdump.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-rich-inputs-20260530T071436Z/windows/weak-helper-c70.objdump.txt`
- `/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-post-callback-contract-20260530T171910Z/post-callback-contract.json`
- `/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-identity-complete-failclosed-20260530T165521Z/resourcehandle-revalidation.json`

Second-source and signature artifacts:

- `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/redacted-minimal/signatures.json`
- `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/snapshot-comparison/readiness-report.json`
- `/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/signatures.json`
- `/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/transfer-scriptstruct-readiness.json`
- `/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack/scriptstruct-inventory.json`

## Blockers And Caveats

- This was an availability audit only. It did not inspect, rerun, or accept gate results.
- No `IsAllowedToBuild` static candidate is promoted by this note.
- Existing `objdump` and `readelf` artifacts remain usable only if their provenance
  sidecars pass the fail-closed rules before contributor-facing claims.
- `/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/normalize-artifact-pack.json`
  is zero bytes and should be treated as unavailable until regenerated.
- Ghidra/radare outputs under `uobject-flag-policy-rich-inputs-*` are offline-available,
  but they remain internal static evidence unless paired with the applicable gate,
  provenance, and promotion contract.

## Result

The local machine has the expected offline static tooling (`radare2` and Ghidra
`analyzeHeadless`) plus a non-protected offline binary and multiple static-policy artifact
packs relevant to build-policy triage. The next useful offline step is to validate the
specific candidate artifact pack for `IsAllowedToBuild` through the repository's
fail-closed offline gate before using it as reusable evidence.

## Follow-up: IsAllowedToBuild Artifact Readiness

Date: 2026-05-30

This follow-up rechecked the current repo and
`/home/flowcommunity-ark/obelisk-artifacts` state for an exact
`PrimalStructure.IsAllowedToBuild` / `APrimalStructure.IsAllowedToBuild` offline artifact.
It did not read or write `/servidor/ark`, start servers, attach to processes, run
ReflectionScanner, or promote any candidate.

Validation results:

- Fixture readiness for both exact targets still reports `missing_base_snapshot`,
  `layout_ready=false`, and `promotion_ready=false`.
- No current non-protected artifact filename or JSON payload under
  `/home/flowcommunity-ark/obelisk-artifacts` contains an exact IsAllowedToBuild snapshot
  or candidate artifact pack.
- The only file larger than 100 MB in that artifact root remains
  `static-global-preflight-20260529/ShooterGameServer.objdump`; no offline core file was
  found there.
- Adjacent structure child manifests are gate-consumable but evidence-only:
  `structure-return-only-policy-slice.json` and
  `structure-nonpin-copied-scalar-policy-slice.json` pass consume mode and block promote
  mode.
- The adjacent structure artifact-pack containers are not currently reusable packs:
  return-only is blocked by the zero-byte `normalize-artifact-pack.json` and embedded
  gate-result JSON, while non-PIN is blocked by the older
  `obelisk.artifact-pack-manifest.v1` schema spelling.
- The static-global preflight manifest is useful historical context for the binary-scoped
  `0x5956f30` FName root slot and `0x595b7e0` GObjects research-candidate, but current
  consume-mode gating blocks it for missing `artifact_identity` and an invalid
  `static_xrefs_sha256`.

Decision: there is no specific IsAllowedToBuild candidate pack to validate yet. The exact
next offline artifact step is to identify or create an approved copied/offline core or
complete core evidence-pack manifest outside protected server paths, for the
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520` binary or a clearly
documented second source. Once that artifact exists and passes path/provenance hygiene,
run the focused snapshot extraction, keeping the reviewed globals binary-hash-scoped:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inspect_core_ufunctions.py \
  --core <approved-offline-core> \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --outer-exact PrimalStructure \
  --name-exact IsAllowedToBuild \
  --inspection-mode ufunction \
  --snapshot-json \
  --evidence-ark-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --evidence-artifact-sha256 <offline-core-or-pack-sha256> \
  --evidence-artifact-kind offline_core \
  --evidence-capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-pack-id> \
  --evidence-obelisk-commit <commit> \
  > <review-output>/PrimalStructure.IsAllowedToBuild.snapshot.json
```

If `APrimalStructure` resolves as a separate reflected owner in the same artifact, repeat
the same command with `--outer-exact APrimalStructure`. Do not add target sets, redacted
signatures, runtime callbacks, descriptors, ABI enums, mutation, return override, or
public Structure SDK surfaces until the candidate snapshot and a distinct second-source
layout comparison exist.

## Offline Snapshot Planner Recheck

Date: 2026-05-30
Obelisk commit: `2186c77`

Scope: offline-only inspection of repository scripts and
`/home/flowcommunity-ark/obelisk-artifacts`. This pass did not read or write
`/servidor/ark`, did not start server operations, did not run ptrace/gcore/scanner tools,
and did not generate a snapshot.

Commands run:

```bash
git rev-parse --short HEAD
git status --short

PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild \
  --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild \
  --json

find /home/flowcommunity-ark/obelisk-artifacts -xdev -type f -size +100M -printf '%s %p\n' | sort -nr
find /home/flowcommunity-ark/obelisk-artifacts -xdev -type l -printf '%p -> %l\n' | sort
find /home/flowcommunity-ark/obelisk-artifacts -xdev \( -iname '*core*' -o -iname '*.core' -o -iname 'core.*' -o -iname '*gcore*' -o -iname '*dump*' \) -printf '%y %s %p -> %l\n' | sort
rg -n --glob '*.json' --glob '*.md' --glob '*.txt' --glob '*.tsv' --glob '!*.objdump' --glob '!ShooterGameServer' \
  'IsAllowedToBuild|AllowedToBuild|BPIsAllowedToBuild|PlacementData|bFinalPlacement|bDontAdjustForMaxRange|PlayerViewRotation|AtLocation|AtRotation' \
  /home/flowcommunity-ark/obelisk-artifacts
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inspect_core_ufunctions.py --help | rg -n -- '--core|--gobjects|--fname-root-slot|--outer-exact|--name-exact|--inspection-mode|--snapshot-json|--evidence-|--max-object-scan'

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.json \
  --mode consume --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/structure-return-only-policy-slice.json \
  --mode promote --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.json \
  --mode consume --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/structure-nonpin-copied-scalar-policy-slice.json \
  --mode promote --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529 \
  --manifest /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume --json
```

Results:

- Both exact readiness checks still report `missing_base_snapshot`, `layout_ready=false`,
  and `promotion_ready=false`.
- The artifact root currently lists 285 files, 66 directories, and 1 symlink. The symlink
  points to the offline binary under
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/.../ShooterGameServer`.
- The only file larger than 100 MB is
  `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump`;
  no eligible raw core file was found under the non-protected artifact root.
- The artifact text search found no exact `IsAllowedToBuild` snapshot, candidate pack, or
  redacted signature under `/home/flowcommunity-ark/obelisk-artifacts`.
- `scripts/inspect_core_ufunctions.py` exposes the required offline snapshot flags:
  `--core`, `--gobjects`, `--fname-root-slot`, `--outer-exact`, `--name-exact`,
  `--inspection-mode ufunction`, `--snapshot-json`, and the evidence identity fields.
- Adjacent structure policy-slice artifacts remain evidence-only: both return-only and
  non-PIN copied-scalar slices pass consume mode and block promote mode.
- Static-global preflight remains useful context for `0x5956f30` and `0x595b7e0`, but
  current consume-mode validation blocks it on `static_global_missing_artifact_identity`
  and `static_global_static_xrefs_sha256_invalid`.
- Some artifact manifests preserve protected core path strings such as
  `/servidor/ark/workspace-offline/.../raw/core`; those manifests are not eligible inputs
  for this task because the requested snapshot must be producible without protected
  paths.

Decision: no eligible core or complete core evidence-pack manifest exists under
`/home/flowcommunity-ark/obelisk-artifacts` for producing a sanitized
`IsAllowedToBuild` snapshot without protected paths.

Exact missing input:

- A copied/offline ELF core file outside `/servidor/ark`, preferably under
  `/home/flowcommunity-ark/obelisk-artifacts/<approved-build-policy-core>/raw/core`, or a
  complete core evidence-pack manifest whose `core.path` resolves outside `/servidor/ark`.
- Matching binary identity for
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, or a clearly
  documented second-source binary hash with its own FName/GObjects evidence.
- Sanitized artifact identity values for `artifact_sha256`, `capture_id`, and
  `evidence_pack_id`.

Command shape once that input exists:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inspect_core_ufunctions.py \
  --core <non-protected-offline-core> \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --outer-exact PrimalStructure \
  --name-exact IsAllowedToBuild \
  --max-object-scan 30000 \
  --inspection-mode ufunction \
  --snapshot-json \
  --evidence-ark-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --evidence-artifact-sha256 <offline-core-or-pack-sha256> \
  --evidence-artifact-kind offline_core \
  --evidence-capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-pack-id> \
  --evidence-obelisk-commit <commit> \
  > <non-protected-review-output>/PrimalStructure.IsAllowedToBuild.snapshot.json
```

If an evidence-pack manifest is supplied instead of a direct core path, first validate that
its `core.path` resolves outside `/servidor/ark`; then use that non-protected resolved
core path in the command above. If the artifact proves `APrimalStructure` is the reflected
owner, rerun the same command with `--outer-exact APrimalStructure`. Do not generate from
or dereference protected `/servidor/ark` paths.
