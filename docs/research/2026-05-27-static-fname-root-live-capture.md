# Static FName root live capture

> Historical capture note. Do not repeat this workflow on `arkserver` / Ragnarok while
> player performance testing is active. Future static-root or ReflectionScanner captures
> should prefer `arkserver-obelisk-debug`; use `arkserver2` / TheIsland only during an
> explicitly approved fallback debug window.

## Objective

Record the historical attempt to validate offline static FName root slot candidate
`0x5956f30` with the `StaticFNameRoot` runtime probe.

## Environment

- Obelisk commit deployed: `5754fca`.
- Server harness: `/servidor/ark/arkserver` Ragnarok development instance.
- Binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Capture env:
  - `OBELISK_ENABLE_REFLECTION_SCANNER=1`
  - `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`
  - `OBELISK_DISABLE_PLUGINS=1`
  - native exec probes remained unset by wrapper

## Method

The historical runtime was deployed with:

```bash
./scripts/install_obelisk.sh --backup-existing /servidor/ark/obelisk
```

Ragnarok was restarted once with the capture env, logs were analyzed, then Ragnarok was
restarted again without scanner/static-root env. This is no longer the approved repeat
pattern; use `arkserver-obelisk-debug` first for any future scanner/static-root capture.

Analyzer artifacts:

```text
/tmp/obelisk-static-root-capture.json
/tmp/obelisk-static-root-ragnarok-capture.json
```

## Evidence

Both `Obelisk.log` and `Obelisk-Ragnarok.log` recorded:

```text
[ReflectionScanner] StaticFNameRoot probing 1 env-supplied slot(s).
[ReflectionScanner] StaticFNameRoot FName static-root reject: slot=0x5956F30 table=0x0 reason=unreadable_table_header readable_clues=0/3 matched_clues=0/3 header_index_ok=0/3 num_elements=0 num_chunks=0 none='' client_message='' server_chat=''
```

Analyzer summary:

- evidence status: `inconclusive`
- static FName root probes: `0`
- static FName root rejects: `1`
- reject reason: `unreadable_table_header`
- UObject validations still appeared for chat-related globals: `22`
- no FName/GNames candidate was accepted

Post-capture server state:

- Ragnarok running again as `arkserver`.
- `OBELISK_ENABLE_REFLECTION_SCANNER` absent from process env.
- `OBELISK_REFLECTION_STATIC_FNAME_ROOTS` absent from process env.
- `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1`.
- `OBELISK_DISABLE_PLUGINS=1`.

## Result

The startup probe does not confirm `0x5956f30`. At scanner startup, the slot value was
`0x0`, so it cannot be treated as a FName/GNames root from this evidence.

This does not fully disprove the static analysis. It may mean:

- the slot is initialized later than the startup probe,
- the candidate is a bucket/registry structure rather than the table slot,
- the static candidate interpretation is wrong for this binary.

## Retry Capture After `d3303cb`

Historical retry after adding delayed retries:

```bash
# Historical only: do not run on Ragnarok during player performance testing.
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30
# Start only an approved isolated/debug instance for future retries.
```

Analyzer artifact:

```text
/tmp/obelisk-static-root-retry-capture.json
```

The startup probe still saw a null slot:

```text
slot=0x5956F30 table=0x0 reason=unreadable_table_header
```

From the 5s retry through the 60s retry, the slot resolved consistently to
`0x41f8d660`, but it did not pass the acceptance gate:

```text
slot=0x5956F30 table=0x41f8d660 reason=implausible_num_elements readable_clues=3/3 matched_clues=1/3 header_index_ok=3/3 num_elements=0 num_chunks=0 none='None' client_message='ServerChat' server_chat='SetActiveMissionDebugFlags'
```

Analyzer summary for the two log files:

- evidence status: `inconclusive`
- static FName root probes: `0`
- static FName root rejects: `26`
- static FName root candidates: `0`
- reject reasons:
  - `implausible_num_elements`: `24`
  - `unreadable_table_header`: `2`

The server was restarted normally after the capture. Post-capture env confirmed:

- `OBELISK_ENABLE_REFLECTION_SCANNER` absent
- `OBELISK_REFLECTION_STATIC_FNAME_ROOTS` absent
- `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1`
- `OBELISK_DISABLE_PLUGINS=1`

### Interpretation

`0x5956f30` is no longer a clean `GNames` root candidate under the current clue-index
assumption. The delayed table has internally consistent entry headers for the tested
indices, and it can read plausible names, but the expected names are shifted:

- index `0` -> `None`
- index `9619` -> `ServerChat`
- index `9622` -> `SetActiveMissionDebugFlags`

This strongly suggests one of these:

- the static slot points at a valid name-like structure but our assumed clue indices are
  from a different name table/order;
- `ClientMessage=9619` and `ServerChat=9622` are not stable for this runtime name table;
- the table header/count interpretation for this structure differs from legacy
  `TNameEntryArray`.

Do not promote `0x5956f30` as accepted `GNames`. Treat it as a useful negative/partial
signal and pivot to deriving clue indices from observed `UObject.NamePrivate` values or
from the table contents itself.

## Next steps

- Stop treating `ClientMessage=9619` and `ServerChat=9622` as fixed acceptance clues for
  this table.
- Add a bounded table-content sampler for explicit static roots that reads selected
  indices and/or a short range around observed `UObject.NamePrivate` indices, still gated
  behind `OBELISK_REFLECTION_STATIC_FNAME_ROOTS`.
- Use observed `UObject.NamePrivate` values from `ServerChat`, `ClientMessage`, and related
  objects to validate `FName -> string` instead of relying only on prior hardcoded clue
  indices.
