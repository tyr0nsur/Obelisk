# Static Xref Validation For GNames Candidates

## Objective

Add an offline validation step between `ReflectionScanner` log triage and any future
promotion of a `GNames`/`FNamePool` candidate.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Scope: analyzer and research documentation only.
- Runtime servers: not touched.
- Native exec probes: not used.
- GitHub publication: left to the team lead.

## Hypothesis

When `ReflectionScanner` logs a repeated `FName indirect-table probe`, the
`source_global` values should have static references in the stripped
`ShooterGameServer` binary. Finding those references does not prove `GNames`, but it helps
separate real UE-generated globals from accidental pointer-table matches.

## Method

The analyzer now accepts a pre-generated objdump text file:

```bash
objdump -d /path/to/ShooterGameServer > /tmp/ShooterGameServer.objdump
python3 scripts/analyze_reflectionscanner_capture.py \
  --json \
  --objdump-xrefs /tmp/ShooterGameServer.objdump \
  /path/to/isolated/Obelisk.log
```

For each parsed `source_global` and `candidate global`, the analyzer searches objdump
comments such as:

```text
mov %rbx,0x1effe9(%rip) # 0x600000
```

and reports matching instruction addresses under `static_xrefs`.

## Acceptance Criteria

Treat the result as stronger research evidence only when all of these hold:

- The table is already a `research-candidate` in analyzer output.
- At least one `source_global` for that table has static xrefs.
- The xrefs are consistent with a global load/store path, not only nearby unrelated code.
- A second isolated capture or deeper static analysis reproduces the same candidate.

Do not accept a runtime offset from static xrefs alone.

## Rejection Criteria

Reject or downgrade the candidate when:

- The analyzer has no repeat-confirmed `GNames` table candidate.
- All candidate `source_global` values have zero static xrefs.
- The only references are unrelated immediate comments or disassembly artifacts.
- The candidate depends on `NativeExecProbe`, legacy plugin markers, or live-server
  discovery.

## Result

Implemented a passive `--objdump-xrefs` analyzer option and unit tests covering JSON and
human output. This adds an offline bridge from log candidates to static binary evidence
without touching C++, CMake, CI, runtime markers, or `/servidor/ark`.

## Next Steps

1. Use this option after the next isolated `ReflectionScanner` capture.
2. If a repeated exact candidate appears, inspect its xrefs with:

```bash
objdump -d --start-address=0xADDR_BEFORE --stop-address=0xADDR_AFTER /path/to/ShooterGameServer
```

3. Document whether each xref is a load, store, initializer path, or unrelated reference.
4. Only after static and repeated runtime evidence agree, design a guarded name-resolution
   experiment.
