---
name: obelisk-static-binary-analysis
description: "Use when Obelisk work needs offline analysis of ShooterGameServer or other ELF binaries with hashes, sections, disassembly, xrefs, Ghidra/rizin/radare evidence, and reproducible candidate validation before runtime probing."
---

# Obelisk Static Binary Analysis

Use this skill before accepting offsets, globals, function candidates, or UE4 reflection
claims from a stripped Linux server binary.

## Ground Rules

- Static analysis is evidence, not proof by itself. Promote candidates only after static
  evidence plus an isolated runtime capture or a second independent static path.
- Never infer a stable SDK contract from one address, one string xref, or one analyzer row.
- Record binary hash, command, tool version when available, and the Obelisk commit used.
- Do not edit protected live-server paths while doing offline analysis. Copy artifacts to
  `/tmp`, `/servidor/ark/workspace-offline`, or another documented offline research
  workspace.
- Static/offline tooling must reject protected server paths in both forms: the expanded
  path textually under `/servidor/ark`, and the resolved path after following symlinks.
  This blocks both symlinks inside the protected root that point outward and symlinks
  outside the root that point inward. The approved under-`/servidor/ark` offline workspace
  is `/servidor/ark/workspace-offline`; prefer hardlinks there for large cores so evidence
  tools do not duplicate 7-11 GB dumps.
- Pre-existing `objdump`/`readelf` text used as static evidence must have a sibling
  `<artifact>.provenance.json` with `verified=true`, matching `binary_sha256`, and matching
  `artifact_sha256`. Missing, unverified, mismatched, malformed, or `/servidor/ark`-
  resolving sidecars are fail-closed evidence blockers. Sidecars that resolve to
  `/servidor/ark/workspace-offline` are allowed when the artifact is part of an approved
  offline workspace.
- Path fields inside provenance sidecars must be checked after resolving relative paths
  against the sidecar directory; do not ignore relative `../...` paths when applying
  protected-path rules.
- Use `scripts/validate_offline_artifact_gate.py` as the passive fail-closed gate for
  reusable offline manifests, redacted signature packs, and static artifacts before
  contributor-facing claims. Passing the gate validates path/provenance hygiene only; it
  does not promote GObjects, UFunction ABI contracts, object identity, mutation, return
  override, `ResourceHandle`, or cross-binary portability.
- Reusable strict evidence for static-global, UObject flag-policy, GObjects
  reconciliation, and ResourceHandle revalidation must carry complete top-level
  `artifact_identity`. Do not infer identity from bare hashes. Reject partial identity,
  mismatched canonical hashes, or placeholder/default ids such as `unspecified-*` and
  producer defaults like `static-global-default-*`; regenerate with current producers and
  `--strict-artifact-identity` when that mode exists.
- New manifest schemas must be added to the gate's supported-schema allowlist with
  schema-specific validation before consume/promote acceptance. Unknown schemas are
  blockers even when generic path/claim scans look clean.
- `obelisk.uobject-flag-policy-report.v1` reports are consume-mode static candidates only.
  The gate must keep them `candidate_blocked`, require explicit non-claims/blockers, and
  reject promote mode; do not use them as accepted `ResourceHandle` or post-callback
  lookup evidence while raw objdump provenance or lifecycle semantics are incomplete.
  If a report consumes weak-helper `caller_rows`, it must summarize them as internal
  caller-mode hygiene only and carry a source weak-helper artifact hash plus caller-row
  digest. Do not copy raw caller addresses into the report or use `caller_rows` to promote
  lifecycle names, public object identity, `ResourceHandle`, lookup, mutation, or return
  override.
- `obelisk.uobject-flag-transition-matrix.v1` reports are provenance-gated static
  candidates only. They may organize helper-window evidence for `UObject+0x8` bits such
  as `0x100`, `0x4000`, and `0x8000`, but they must stay `candidate_blocked` and must not
  assign public lifecycle names, promote `ResourceHandle`, or claim post-callback lookup
  safety without runtime negative samples and an accepted lookup contract. The offline
  artifact gate may accept them in consume mode for indexing and must block promote mode.
- `obelisk.uobject-flag-semantic-correlation.v1` reports are also candidate-only. The gate
  must require `candidate_blocked`, explicit non-claims/blockers, a fail-closed builder
  contract, redacted binary/source-pack fields, and verified per-input provenance before
  consume-mode use. Existing semantic packs without that contract are useful notes only,
  not gated artifacts.
- Weak-helper polarity/caller-mode reports are accepted internal static evidence only.
  They may classify helper return polarity and caller mode for a specific binary hash, but
  they must not assign public lifecycle names, promote `ResourceHandle`, claim
  post-callback lookup safety, or clear `uobject_flags_validity_semantics_unproven`.
  Consume-mode gate acceptance is hygiene/indexing only; promote mode remains blocked
  until rejected runtime object samples and an accepted lookup contract exist.
  Normalized reports may preserve boolean-like and pointer-or-null helper summaries when
  redacted, but those summaries remain internal static evidence only.
- Weak-helper caller-mode redacted reports that hash raw Ghidra/radare inputs but do not
  require verified sidecar provenance stay candidate consume-mode only. Before using a new
  caller-mode artifact as reusable promotion support, add or verify fail-closed provenance
  sidecars for each raw static input, matching the binary hash and artifact hash.
- `obelisk.uobject-flag-sample-report.v1` reports combine existing UObject flag static
  artifacts for blocker accounting only. The gate may accept them in consume mode, but
  promote mode must stay blocked until rejected runtime object samples, post-callback
  lifetime policy, and a public lookup/revalidation contract exist.
- `obelisk.resource-handle-serial-scan.v1` is an internal/offline scan artifact only.
  Consume-mode acceptance requires coherent `flag_rejection_candidate_samples` plus a
  required `scan_limit` that matches provenance and bounds sparse candidate indices;
  promote mode must stay blocked and the artifact must not be cited as public handle,
  lookup, or lifecycle promotion evidence.
- Redacted UFunction signature reports that claim a named target set should carry
  `target_set_coverage` metadata. For direct snapshot inputs, pass
  `--source-target-set <name>` to `scripts/build_redacted_ufunction_signatures.py`; for
  review gates, use `scripts/validate_offline_artifact_gate.py
  --strict-target-set-coverage` when the artifact is expected to prove exact target-set
  coverage. Missing or incomplete coverage is a traceability blocker, not a runtime
  promotion signal.
- Reflection snapshot readiness reports are accepted only as named second-source layout
  evidence: `gate_mode=second_source_promotion`, non-empty `target_sets`, and
  `promotion_gate.promotion_ready=false`. Consume-mode acceptance is not public API,
  runtime hook, mutation, return override, or object identity promotion, and promote mode
  must stay blocked until a separate schema-specific promotion contract exists.

## Baseline Evidence Pack

For every candidate offset/global/function, capture:

```bash
sha256sum ShooterGameServer
file ShooterGameServer
readelf -h -W ShooterGameServer
readelf -S -W ShooterGameServer
readelf -l -W ShooterGameServer
objdump -d -M intel ShooterGameServer > /tmp/ShooterGameServer.objdump
```

For reusable static global evidence, prefer
`scripts/build_static_global_promotion_evidence.py` because it writes verified sidecars
beside generated artifacts and records fail-closed blockers for copied artifacts without
trusted provenance.

If available, add:

```bash
rizin -A -q -c 'iz; afl; q' ShooterGameServer
radare2 -A -q -c 'iz; afl; q' ShooterGameServer
```

Use Ghidra for manual decompilation/xref confirmation when command-line evidence is
ambiguous. Save conclusions in `docs/research/`, not screenshots.

Core dump evidence packs must not report ordinary success when GDB core inspection fails.
Use `--allow-partial-gdb` only for triage-only artifacts; such manifests are marked
`partial-gdb-failed` and must not be used as promoted evidence.
Snapshot regenerators that consume `--evidence-pack-manifest` must reject packs whose
`binary.sha256` does not match the snapshot manifest, whose
`evidence_status.status` is not `complete`, or whose `gdb_core_failed` is true.

## Tool Selection

- Start with `readelf`/`objdump`/analyzer evidence because it is reproducible in CI-like
  shell workflows.
- Use Ghidra when the question needs decompiler context, recovered control flow, or manual
  type reasoning.
- Use rizin/radare2 when batchable xrefs or function lists help automate a hypothesis.
- Keep `rr`, Frida, `gdb` attach, and broad runtime instrumentation out of this skill unless
  an isolated debug instance has already been approved.

## Agent Output Contract

Static reversing agents must return an evidence pack, not just a conclusion:

- binary path and SHA256,
- exact commands,
- candidate addresses with segment/range,
- xref summary,
- accepted/rejected status,
- next validation needed.

## Candidate Workflow

1. Start from a clue: string, ReflectionScanner candidate, pattern hit, crash address, or
   known UE4 type shape.
2. Confirm the address belongs to the expected ELF segment or loaded runtime range.
3. Find xrefs from code and data. Prefer RIP-relative references over broad string
   proximity.
4. For `GUObjectArray`/`GObjects`, do not accept globally aggregated root/chunks/count/serial
   references as one coherent static path. Require code-backed RIP-relative field xrefs in
   one non-oversized instruction window before treating the static contract as satisfied.
5. Explain how the value flows: initialization store, global load, vtable reference, or
   constructor path.
6. Reject candidates with single-source evidence, implausible counts, mismatched previews,
   or no executable/data xref path.
7. Feed copied logs plus objdump evidence into:

```bash
python3 scripts/analyze_reflectionscanner_capture.py \
  --json \
  --binary /path/to/ShooterGameServer \
  --objdump-xrefs /tmp/ShooterGameServer.objdump \
  /path/to/isolated/Obelisk.log
```

The JSON output contains an `evidence_pack` block. Preserve that block in the research
note summary when a candidate is promoted to `research-candidate` or explicitly rejected.
Its `promotion_gate` is the machine-readable promotion contract: for ReflectionScanner
packs it must remain `ready=false`, and `promotable.gnames` / `promotable.gobjects` must
remain false until a separate second-source/static promotion artifact exists. Do not use
`evidence_pack.status=research-candidate` alone as a runtime offset or API promotion.

## Acceptance Bar

A candidate may become a research candidate when:

- Binary hash, Obelisk commit, and command trail are recorded in an evidence pack.
- The value is in the expected segment/range.
- Static xrefs explain why the candidate can be a UE4 global/function.
- Runtime analyzer evidence is repeat-confirmed or a second static path supports it.
- Known false positives are explicitly checked.

A candidate may become runtime code only after:

- second isolated capture or static xref validation,
- bounds checks and reject logs exist,
- rollback is documented,
- no live-server-only evidence is required to reproduce the claim.

## Output

Write concise notes under:

```text
docs/research/YYYY-MM-DD-static-<topic>.md
```

Include objective, environment, commands, evidence, rejected paths, result, risks, and next
steps. Keep raw objdump files out of Git.
