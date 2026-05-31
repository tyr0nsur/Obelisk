# Offline Evidence Pack Tooling Audit

## Objective

Audit the current offline evidence tooling for `ShooterGameServer`/Obelisk log analysis and
add one small reproducibility improvement without touching the live ARK harness.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Scope: scripts and research documentation only.
- Server state: not modified.
- Runtime probes: not used.
- GitHub/commits: left to the team lead.

## Current Tooling

Existing useful pieces:

- `scripts/analyze_reflectionscanner_capture.py` parses copied ReflectionScanner logs,
  `FName` probes/rejects, static-root probes/samples, delayed globals, candidate globals,
  and UObject validation scores.
- The analyzer accepts `--binary` and records SHA256/size in `evidence_pack.binary`.
- The analyzer accepts `--objdump-xrefs` and classifies static references as `load`,
  `store`, `address`, `call`, `jump`, or `other`.
- `scripts/test_analyze_reflectionscanner_capture.py` has offline fixture coverage for
  strict mode, false positives, static-root evidence, samples, static xrefs, and binary
  metadata.
- `docs/research/2026-05-27-gname-evidence-pack-workflow.md` documents the manual
  `sha256sum`/`readelf`/`objdump`/analyzer flow.
- `docs/research/2026-05-27-current-gname-evidence-pack-audit.md` records the current
  binary hash and explains why available logs are inconclusive.

Gap found:

- Evidence pack collection was still a manual command sequence. Different maintainers or
  runs could omit `readelf`, forget to copy logs, analyze original live log paths, or write raw
  artifacts into unsafe locations.

## Change

Added `scripts/build_reflection_evidence_pack.py`.

The script:

- requires `--binary`, `--output-dir`, and copied log paths;
- refuses to write artifacts under `/servidor/ark`;
- copies logs into `<output-dir>/logs/`;
- writes `ShooterGameServer.sha256.txt`, `file`, `readelf -h/-S/-l`, and
  `objdump -d -M intel` artifacts;
- runs `scripts/analyze_reflectionscanner_capture.py --json --binary --objdump-xrefs`
  against the copied logs;
- writes `manifest.json` with binary hash, copied logs, artifact paths, exact commands,
  return codes, and the promotion gate.

Example:

```bash
python3 scripts/build_reflection_evidence_pack.py \
  --binary /path/to/ShooterGameServer \
  --output-dir /tmp/obelisk-evidence-YYYYMMDD-topic \
  /path/to/copied/Obelisk.log
```

## Recommended Method

Use this order:

1. Offline first: copied logs plus copied/read-only binary metadata through
   `scripts/build_reflection_evidence_pack.py`.
2. Static follow-up: inspect relevant objdump windows or Ghidra/rizin decompiler context
   only after the analyzer identifies a concrete candidate/source global.
3. Isolated runtime only: run `ReflectionScanner`, `gdb`, `rr`, Frida, or dynamic
   instrumentation only on a confirmed isolated debug instance such as the planned
   `arkserver-obelisk-debug`.
4. Reference comparison only: Wine/Windows builds can help compare UE4 naming patterns or
   public-symbol/tutorial assumptions, but they should not validate Linux offsets for this
   stripped `ShooterGameServer` binary.

Avoid:

- enabling scanner/native probes on live/shared ARK;
- using live log paths as the durable artifact instead of copied logs;
- promoting `0x5956f30` or any other slot from static evidence alone;
- treating the 44 `implausible_num_elements` samples as a negative proof of the table.

## Validation

Ran:

```bash
python3 scripts/test_analyze_reflectionscanner_capture.py
```

Result:

```text
Ran 25 tests in 2.737s
OK
```

The new tests validate that the evidence-pack builder creates static/analyzer artifacts
from an offline ELF and copied log, and rejects an output directory under `/servidor/ark`.

## Risks

- `objdump` artifacts can be large and must stay out of Git.
- Historical note: this audit predates the current protected-path rules. Current evidence
  builders must reject protected server roots except for explicitly approved offline
  workspaces; prefer `docs/OFFLINE_ARTIFACT_PACKS.md` and the current script help over
  copying the old `/servidor/ark` examples from this note.
- Analyzer output remains evidence only. It does not accept offsets or runtime code.

## Next Steps

1. Use the builder for the next isolated ReflectionScanner capture after the operator
   designates `arkserver-obelisk-debug` or another isolated instance.
2. Keep `0x5956f30` as a research-candidate only; do not promote it until a pack shows
   exact clues or a stronger independent static path.
3. If a candidate appears, inspect the specific objdump xref windows and record whether
   each reference is a real load/store/initializer path or unrelated immediate text.
