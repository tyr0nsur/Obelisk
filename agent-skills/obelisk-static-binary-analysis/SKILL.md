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
- Do not edit `/servidor/ark` while doing offline analysis. Copy artifacts to `/tmp` or a
  documented research workspace.
- Static/offline tooling must reject protected server paths in both forms: the expanded
  path textually under `/servidor/ark`, and the resolved path after following symlinks.
  This blocks both symlinks inside the protected root that point outward and symlinks
  outside the root that point inward. The approved under-`/servidor/ark` offline workspace
  is `/servidor/ark/workspace-offline`; prefer hardlinks there for large cores so evidence
  tools do not duplicate 7-11 GB dumps.
- Pre-existing `objdump`/`readelf` text used as static evidence must have a sibling
  `<artifact>.provenance.json` with `verified=true`, matching `binary_sha256`, and matching
  `artifact_sha256`. Missing, unverified, mismatched, malformed, or `/servidor/ark`-
  resolving sidecars are fail-closed evidence blockers.

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
