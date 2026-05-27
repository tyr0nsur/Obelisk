# Static FName root live capture

## Objective

Validate the offline static FName root slot candidate `0x5956f30` with the new
`StaticFNameRoot` runtime probe.

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

The runtime was deployed with:

```bash
./scripts/install_obelisk.sh --backup-existing /servidor/ark/obelisk
```

Ragnarok was restarted once with the capture env, logs were analyzed, then Ragnarok was
restarted again without scanner/static-root env.

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

## Next steps

- Add a delayed static-root retry using the same env-supplied slots and the same
  `header_index_ok=3/3` acceptance gate.
- If the delayed retry still sees `table=0x0`, return to static xrefs around
  `0x1c88e70`, `0x1c89a70`, and `0x1c990d0` before adding broader runtime probes.
