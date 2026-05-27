# Static Root Runtime Retry Capture

Superseded note: this capture is useful historical evidence, but later post-start
debug-control probing showed that waiting longer in bootstrap is not a coherent primary
strategy. New work should prefer post-start probes, offline core evidence packs, or
bounded live data-mapping scanners.

Historical Ragnarok capture note. Do not repeat this workflow on `arkserver` / Ragnarok.
Future static-root, ReflectionScanner, or debug-control probes must prefer
`arkserver-obelisk-debug`; `arkserver2` / TheIsland is only an explicit
operator-approved fallback with rollback and posture evidence.

## Objective

Retest `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30` after correcting the static
FName clue indices from core-dump evidence.

## Environment

- Repo head before this note: `c7ccdb6`
- Server: historical `arkserver` / Ragnarok capture; not a current debug target
- Runtime env during capture:
  - `OBELISK_ENABLE_REFLECTION_SCANNER=1`
  - `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`
  - `OBELISK_REFLECTION_LOG_FNAME_REJECTS=1`
  - plugins disabled
  - native exec probes unset
- Capture directory:
  `/servidor/ark/obelisk/dumps/static-root-capture-20260527T032535Z`
- Stable posture after capture: historically restored and verified with the posture check
  available at that time. Current debug targets should use explicit `--map` and
  `--instance` posture checks.

## Evidence

Startup probe:

```text
StaticFNameRoot FName static-root reject: slot=0x5956F30 table=0x0 reason=unreadable_table_header
```

Delayed retries from 5s through 60s all read the same table pointer:

```text
table=0x30752660
reason=implausible_num_elements
readable_clues=0/3
matched_clues=0/3
header_index_ok=0/3
num_elements=0
num_chunks=0
```

The server was then restarted without scanner env. A later stable posture check showed no
scanner/static-root env variables.

## Result

The runtime capture is still inconclusive, not negative. The core dump already proves that
`0x5956f30` can point to a valid FName table in an initialized process, but the startup
ReflectionScanner capture only retries for 60 seconds and can still observe an
uninitialized table.

## Change

Increase static-root delayed retry coverage from 60 seconds to 10 minutes, matching the
existing global-watch retry window. This is low risk: it only runs when
`OBELISK_REFLECTION_STATIC_FNAME_ROOTS` is explicitly set, and it reads bounded clue
entries from env-supplied slots.

## Next Steps

1. Deploy the longer retry build.
2. Run one static-root scanner capture only on `arkserver-obelisk-debug`, or on
   `arkserver2` during an approved fallback window, and wait at least 10 minutes before
   copying logs.
3. Analyze with `scripts/analyze_reflectionscanner_capture.py --strict`.
4. If it still rejects with zero clues, add static-root reject detail for first clue
   failure and consider validating from a post-start on-demand trigger rather than startup
   bootstrap.
