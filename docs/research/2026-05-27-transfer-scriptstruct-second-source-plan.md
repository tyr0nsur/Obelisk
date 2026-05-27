# Transfer ScriptStruct Second-Source Plan

## Objective

Define the next gate for `ARKTributeDino` and `ArkTributePlayerData` after adding
candidate-only ScriptStruct fixtures, without using live runtime probes.

## Environment

- ScriptStruct manifest:
  `tests/fixtures/scriptstruct_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Offline core SHA256:
  `1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e`
- Obelisk baseline:
  `016778a Add transfer ScriptStruct snapshot fixtures`
- Live-server impact: none.

## Current Evidence

The committed fixtures validate that the current offline core exposes:

| Struct | Outer | PropertiesSize | Observed Fields | Fixture Status |
| --- | --- | ---: | ---: | --- |
| `ARKTributeDino` | `PrimalLocalProfile` | 288 | 10 | candidate-only |
| `ArkTributePlayerData` | `PrimalLocalProfile` | 288 | 11 | candidate-only |

Both fixtures are reproducible with:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --obelisk-commit 0e11b07 \
  --check
```

For future second-core comparison, prefer layout-only comparison so an expected
`obelisk_commit` metadata change does not mask or fabricate layout drift:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/second/offline/core \
  --obelisk-commit <current-commit> \
  --check-layout
```

## Second-Source Options

1. Best: another isolated offline core from `arkserver2` or a dedicated debug instance,
   captured during an approved window with plugins disabled.
2. Acceptable auxiliary source: static binary evidence that confirms symbol/string
   families or constructor/use sites. This can support confidence but cannot prove runtime
   field offsets alone.
3. Not acceptable: Ragnarok captures while players are performance-testing, broad
   `ProcessEvent` discovery, ptrace/gcore without an approved debug window, or decoding
   transfer payload buffers in runtime callbacks.

## Static Evidence Status

The current `ShooterGameServer.strings.txt` contains `ItemNetInfo` references, including
server-side prevention messages and `GetItemNetInfo`. It did not expose the two tribute
struct names in the string dump searched during this round. That means static strings are
useful for keeping `ItemNetInfo` high-risk, but they are not a second source for the two
tribute layouts.

## Result

No independent second source is currently available in the local artifacts. The existing
fixtures should stay `candidate-only`; they are suitable for regression guardrails and
offline planning, not SDK promotion or runtime transfer decoding.

## Rejected Paths

- Promoting `ARKTributeDino` or `ArkTributePlayerData` to public SDK payload contracts.
- Adding `ItemNetInfo` as a committed fixture before nested struct/array policy exists.
- Capturing or decoding transfer payloads on Ragnarok.

## Next Steps

1. Prepare an approved debug-window checklist for `arkserver2` or a dedicated debug
   instance to produce a second core.
2. Re-run ScriptStruct regeneration against that second core with `--check-layout` and
   compare field names, offsets, sizes, array inners, and `properties_size`.
3. Document mismatches as blockers; only matching layouts can move from single-core
   fixture evidence toward runtime-observed planning.
