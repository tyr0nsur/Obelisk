# Current GNames Evidence Pack Audit

## Objective

Check whether the currently available local binary and Obelisk logs are enough to produce a
useful `GNames`/`FNamePool` evidence pack without touching server state.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit: `0820ab60ac72`
- Binary: `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- Logs checked:
  - `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`
  - `/servidor/ark/obelisk/logs/arkserver/Obelisk-Ragnarok.log`
- Offline artifact root: `/tmp/obelisk-gname-evidence-20260527`
- Server state: not modified
- Runtime probes: not enabled

## Method

Commands used:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -h -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -S -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -l -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
objdump -d -M intel /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer > /tmp/obelisk-gname-evidence-20260527/ShooterGameServer.objdump
rg -n "ReflectionScanner|FName indirect-table|GNames|NativeExecProbe|LegacyPlugin|candidate global|delayed global|UObject validation" /servidor/ark/obelisk/logs/arkserver/Obelisk.log /servidor/ark/obelisk/logs/arkserver/Obelisk-Ragnarok.log
python3 scripts/analyze_reflectionscanner_capture.py --json --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer --objdump-xrefs /tmp/obelisk-gname-evidence-20260527/ShooterGameServer.objdump /tmp/obelisk-gname-evidence-20260527/Obelisk.log /tmp/obelisk-gname-evidence-20260527/Obelisk-Ragnarok.log
python3 scripts/analyze_reflectionscanner_capture.py --strict --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer --objdump-xrefs /tmp/obelisk-gname-evidence-20260527/ShooterGameServer.objdump /tmp/obelisk-gname-evidence-20260527/Obelisk.log /tmp/obelisk-gname-evidence-20260527/Obelisk-Ragnarok.log
```

## Evidence

Binary SHA256:

```text
7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

ELF summary:

- Type: `EXEC`
- Machine: `x86-64`
- Entry point: `0x81dc59`
- `.text`: `0x648400 - 0x3f6170f`
- `.rodata`: starts at `0x3f61740`
- `.data`: starts at `0x5825080`
- `.bss`: starts at `0x58446c0`

Program header summary:

- executable `LOAD`: file offset `0x0`, virtual range `0x400000 - 0x5604aac`
- writable `LOAD`: file offset `0x5205000`, virtual range `0x5805000 - 0x5a25b90`

Generated offline artifacts:

- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.sha256.txt`
- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.file.txt`
- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.readelf-header.txt`
- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.readelf-sections.txt`
- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.readelf-programs.txt`
- `/tmp/obelisk-gname-evidence-20260527/ShooterGameServer.objdump`
- `/tmp/obelisk-gname-evidence-20260527/analyzer-evidence.json`

Available live harness logs only contain:

```text
ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.
```

Analyzer result on the current log:

- evidence status: `inconclusive`
- candidate globals: `0`
- delayed globals: `0`
- UObject validations: `0`
- FName probes: `0`
- GNames table triage: none
- reject markers: none
- static xref access counts: none, because there were no scanner candidate globals to
  annotate

Evidence pack summary:

```json
{
  "binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
  "obelisk_commit": "0820ab60ac72",
  "fname_probe_count": 0,
  "gname_table_candidate_count": 0,
  "reject_marker_count": 0,
  "static_xref_access_counts": {},
  "status": "inconclusive"
}
```

Strict analyzer mode exited non-zero as expected:

```text
FName exact candidates: 0
FName repeat-confirmed candidates: 0
GNames table triage:
- none
```

## Result

The current logs are not sufficient to produce a `GNames`/`FNamePool` research candidate.
This is expected: `ReflectionScanner` was disabled in the checked logs, so there are no
`FName indirect-table probe` rows for the analyzer to group or cross-check.

This audit still establishes the current binary hash and ELF ranges needed for the next
proper evidence pack.

## Rejected Paths

- Did not generate or promote any offset.
- Did not run `ReflectionScanner`.
- Did not run native exec probes.
- Did not restart or modify `/servidor/ark`.
- Did not treat absence of evidence as a negative result about `GNames`; it only means the
  available logs lack the needed capture.

## Next Steps

1. Create or designate an isolated debug instance before enabling `ReflectionScanner`.
2. Capture logs with `OBELISK_ENABLE_REFLECTION_SCANNER=1`, plugins disabled, and native
   exec probes unset.
3. Generate objdump for the same binary:

```bash
objdump -d -M intel /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer > /tmp/ShooterGameServer.objdump
```

4. Run:

```bash
python3 scripts/analyze_reflectionscanner_capture.py \
  --json \
  --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  --objdump-xrefs /tmp/ShooterGameServer.objdump \
  /path/to/copied/isolated/Obelisk.log
```

5. Accept only `research-candidate` evidence with repeat-confirmed table clues and static
   xrefs that classify as meaningful access paths.
