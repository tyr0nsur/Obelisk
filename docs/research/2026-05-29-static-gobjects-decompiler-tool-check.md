# Static GObjects Decompiler Tool Check

## Objective

Continue the bounded decompiler/static plan from
`2026-05-29-static-gobjects-fuobjectitem-correlation.md` by checking whether local
Ghidra/rizin/radare tooling is available for the fixed `FUObjectArray` ranges. Do not run
broad analysis, runtime probes, or live-server operations.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Obelisk commit: `a6b2649`
- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Binary type: ELF64 x86-64 executable, dynamically linked, stripped
- Live-server impact: none

## Commands

```bash
command -v rizin || true
command -v rz-bin || true
command -v rz-ghidra || true
command -v r2ghidra-dec || true
command -v radare2 || true
command -v r2 || true
command -v analyzeHeadless || true
command -v ghidraRun || true
command -v ghidra || true

for p in /opt/ghidra* /usr/share/ghidra* /usr/local/bin/analyzeHeadless \
  /usr/bin/analyzeHeadless /snap/bin/ghidra /snap/bin/radare2 /snap/bin/rizin \
  /usr/bin/rizin /usr/bin/radare2 /usr/bin/r2 /usr/local/bin/rizin \
  /usr/local/bin/radare2 /usr/local/bin/r2; do
  [ -e "$p" ] && printf '%s\n' "$p"
done

dpkg-query -W -f='${binary:Package}\t${Version}\n' 'rizin*' 'radare2*' 'ghidra*' \
  2>/dev/null || true

git rev-parse --short HEAD
sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
file /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

jq '.promotion_gate, (.candidates[] | select(.label=="gobjects") | .static_contract.blockers)' \
  /tmp/obelisk-static-gobjects-near-miss-20260529/manifest.json
```

## Evidence

The `command -v` checks produced no executable path for:

- `rizin`, `rz-bin`, `rz-ghidra`, or `r2ghidra-dec`
- `radare2` or `r2`
- `analyzeHeadless`, `ghidraRun`, or `ghidra`

The common-location probe produced no paths under `/opt`, `/usr/share`, `/usr/bin`,
`/usr/local/bin`, or `/snap/bin` for the checked Ghidra/rizin/radare names.

The package probe produced no installed `rizin*`, `radare2*`, or `ghidra*` dpkg records.

The local binary identity still matches the bounded plan:

```text
commit: a6b2649
sha256: 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
file: ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
```

The static manifest gate remains:

```json
{
  "ready": false,
  "blockers": [
    {"reason": "static_only_evidence"},
    {
      "reason": "candidate_static_contract_blocked",
      "candidate": "gobjects",
      "blockers": ["missing_gobjects_coherent_field_window"]
    }
  ]
}
```

The candidate-specific static contract blockers remain:

```json
["missing_gobjects_coherent_field_window"]
```

## Fallback

No Ghidra headless, rizin, or radare2 fixed-range decompiler/disassembly command was
available to run. The fallback is the already recorded bounded `objdump` evidence in
`2026-05-29-static-gobjects-fuobjectitem-correlation.md`, covering only:

- `0x1d4a8b0..0x1d4aa18` root/chunks/count init
- `0x1d56970..0x1d56a26` weak-handle serial publish from `UObject` index
- `0x1d56d60..0x1d56ecd` repeated handle validate/publish path

That fallback corroborates instruction-level compatibility between the object membership
path and the serial path through `0x595b7f0` and `0x595b804`, but it does not provide
decompiler/type recovery proving `0x595b838` is `base+0x58` of the same `FUObjectArray`
rooted at `0x595b7e0`.

## Result

The same-instance blocker did not move. `0x595b7e0` remains a binary-hash-specific
`GUObjectArray` research candidate only, not a promoted runtime global.

Remaining blocker:

```text
no bounded decompiler/static path proves 0x595b838 is base+0x58 of the same FUObjectArray rooted at 0x595b7e0
```

## Next Steps

Install or provide one bounded decompiler-capable tool path, preferably Ghidra headless
with an existing project or a temporary no-auto-analysis project. If only rizin/radare is
available later, run only the fixed seeks from the plan and treat the output as
instruction-level corroboration unless it recovers a local base-derived access.

## 2026-05-29 Tooling Update

`radare2` and Ghidra headless are now installed and usable:

```text
/usr/bin/r2
/usr/local/bin/analyzeHeadless
```

Smoke test:

```bash
mkdir -p /servidor/ark/workspace-offline/ghidra-smoke
timeout 120 analyzeHeadless \
  /servidor/ark/workspace-offline/ghidra-smoke ObeliskSmoke \
  -import /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  -noanalysis \
  -deleteProject
```

Result: import succeeded with the expected ELF copy-relocation warnings and no runtime
server impact. This only proves the toolchain can import the offline binary; it does not
resolve `missing_gobjects_coherent_field_window` or promote `GUObjectArray`.
