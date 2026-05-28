# Structure Observation Runbook

## Objective

Define the safe operator path for the disabled-by-default `sdk.structures` observation
gate. This runbook is preparation only; it does not authorize a server restart or runtime
capture.

## Scope

The gate observes only compact, fixture-backed structure functions:

- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureSeating.CanSeat`
- `PrimalStructure.SetVariant`
- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`

It logs target metadata, field offsets, sizes, sensitivity flags, and whether a safe
borrowed scalar range exists. It must not log pincode values, dereference `UObject*`, expose
player identity, or mutate return values.

## Preconditions

- Do not use `arkserver` / Ragnarok while player performance testing is active.
- Prefer a dedicated `arkserver-obelisk-debug` instance.
- Use `arkserver2` / TheIsland only with explicit operator approval for a short debug
  window.
- Instance-scoped marker gates are required:
  `/servidor/ark/obelisk/state/instances/<instance>/allow-experimental-observers`
  plus
  `/servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection`.
  Env-only activation or observer-marker-only activation is rejected by the runtime gate
  and should be treated as a posture error on production-like hosts.
- ProcessEvent hook is enabled for the approved instance.
- Plugins are disabled unless the window explicitly tests one minimal observer plugin.
- Scanner, native exec probes, and broad trace are off.
- The current ARK binary SHA is:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

## Gate

Use the global observer allow marker, the structure marker, and all three
structure-specific variables together:

```bash
touch /servidor/ark/obelisk/state/instances/<instance>/allow-experimental-observers
touch /servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection
export OBELISK_ENABLE_STRUCTURE_REFLECTION=1
export OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
export OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=25
```

The LinuxGSM wrapper exports these variables only when both markers are present. The hook
also checks the markers itself, so manually setting the env without both markers will not
enable observation. The log limit is also the observation budget. When it is absent or
`0`, structure observation does not read `UFunction` names or reflected fields. Keep the
budget small for debug windows.

Keep these unset unless the debug window is active:

```bash
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
unset OBELISK_ENABLE_REFLECTION_SCANNER
export OBELISK_PE_TRACE_LIMIT=0
```

## Expected Logs

Accepted hits should look like metadata-only records:

```text
Reflected structure ProcessEvent #1 function=VerifyPinCode fname_index=7636 outer_fname_index=7617 fields=2
Reflected structure field pinCode offset=0x0 size=4 sensitive=true has_range=false
Reflected structure field ReturnValue offset=0x4 size=1 sensitive=false has_range=true
```

Reject logs may include a reason, but must not include pincode values or raw object data.

## Abort Conditions

Abort the window and return to stable posture if any of these occur:

- logs contain raw pincode values, player identifiers, object addresses, inventories, or
  locations;
- broad `ProcessEvent` trace becomes active unintentionally;
- reject count grows rapidly for the same target;
- server performance or joinability changes;
- the binary SHA gate rejects the server;
- Ragnarok would need to be touched.

## Rollback

Unset the structure gate and restore the approved instance only:

```bash
unset OBELISK_ENABLE_STRUCTURE_REFLECTION
unset OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
unset OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT
rm -f /servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection
```

For TheIsland fallback, verify stable posture after restart:

```bash
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
```

## Evidence To Capture

- Obelisk commit.
- ARK binary SHA.
- Instance id and map.
- Exact gate env.
- Hit/reject counts by target.
- Sanitized log excerpts showing metadata only.
- Post-run stable posture result.

## Current Status

The gate is implemented and tested locally, but no live or debug-server run has been
performed. `sdk.structures` remains internal and experimental.
