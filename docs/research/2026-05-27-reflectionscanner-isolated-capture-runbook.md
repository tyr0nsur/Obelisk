# ReflectionScanner Isolated Capture Runbook

## Objective

Prepare the next isolated `ReflectionScanner` capture to validate two scanner-only signals:

- `UObject validation` score for already-discovered candidate globals.
- `FName indirect-table probe` against index `0 == None`, `9619 == ClientMessage`, and
  `9622 == ServerChat`.

This runbook is for an isolated/debug ARK instance only. Do not use it to enable
raw event discovery or native exec probes on the active development server.

## Environment To Record

- Obelisk commit: record the exact commit under test before each capture; current handoff
  starts from `a33b547`.
- ARK binary path:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256 observed from this workspace:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Instance/map: isolated/debug `OBELISK_INSTANCE_ID` and map.
- Plugins state: disabled.
- Native exec probes: disabled or unset.
- Raw chat discovery: disabled or unset.
- Log path copied after the run, for example the isolated server's `Obelisk.log`.

## Required Flags

Use the existing explicit scanner gate and keep all risky experiments off:

```bash
export OBELISK_ENABLE_REFLECTION_SCANNER=1
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
export OBELISK_PE_TRACE_LIMIT=0
```

There is currently no marker-file gate for `OBELISK_ENABLE_REFLECTION_SCANNER`; it must be
set in the isolated instance environment. Marker files may still be used for the existing
hook/plugin gates, but only through instance markers:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug
touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/disable-plugins
```

Do not remove the plugin-disable marker for this capture. Do not assume that creating an
`enable-reflection-scanner-*` marker will run the scanner unless the launcher has been
explicitly changed to translate that marker into `OBELISK_ENABLE_REFLECTION_SCANNER=1`.

## Capture Commands

From the isolated server control directory, start or restart only the isolated instance:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
git -C /home/flowcommunity-ark/Obelisk rev-parse --short HEAD
git -C /home/flowcommunity-ark/Obelisk status --short
./arkserver restart
```

Let the process reach normal startup and leave it up for at least 10 minutes. The scanner
runs at startup and also has a delayed candidate-global watch that may resolve globals up
to 120 iterations at 5-second intervals.

Collect only the relevant scanner lines:

```bash
rg "ReflectionScanner|NativeExecProbe|ProcessEvent" /path/to/isolated/Obelisk.log
rg "UObject validation|FName indirect-table probe|delayed global resolved" /path/to/isolated/Obelisk.log
```

Then summarize the copied log without touching the server:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/isolated/Obelisk.log
```

The analyzer extracts candidate globals, delayed globals, top `UObject validation` scores,
`FName indirect-table probe` rows, and reject markers such as `[NativeExecProbe] installed`
or legacy plugin markers. Use `--strict` only in offline analysis when a non-zero exit should mean
that reject markers were present or no repeat-confirmed exact `matched_clues=3/3` FName
research candidate was found.

## Expected Logs

Startup scan:

```text
[ReflectionScanner] Scanning <n> ShooterGameServer mapping(s): <n> readable, <n> executable.
[ReflectionScanner] target=ServerChat utf32_strings=<n> refs=<n> globals=<n>
[ReflectionScanner] <target> candidate global 0x<addr> -> <ptr>
```

UObject validation signal:

```text
[ReflectionScanner] <target> UObject validation: object=<ptr> score=<n>/6 vtable_exec=<bool> class_readable_or_null=<bool> outer_readable_or_null=<bool> fname_plausible=<bool> flags_plausible=<bool> internal_plausible=<bool>
```

FName indirect-table signal:

```text
[ReflectionScanner] <target> FName indirect-table probe: source_global=0x<global> table=<ptr> score=<n>/8 readable_clues=<n>/3 matched_clues=<n>/3 num_elements=<n> num_chunks=<n> none='<name>' client_message='<name>' server_chat='<name>'
```

Delayed resolution, if a static candidate becomes initialized after startup:

```text
[ReflectionScanner] delayed global resolved after <seconds>s: <target> 0x<global> -> <ptr>
```

Reject the capture immediately if it contains:

```text
[NativeExecProbe] installed
legacy plugin markers
```

## Accept Or Reject GNames

Accept a `GNames` candidate only as a research candidate, not as a committed offset, when all
of these are true in one capture:

- The `FName indirect-table probe` line reports `matched_clues=3/3`.
- The preview values are exactly `none='None'`, `client_message='ClientMessage'`, and
  `server_chat='ServerChat'`.
- `num_elements` is greater than `9622` and plausible for the binary.
- `num_chunks` is positive and no more than the scanner's probe maximum.
- The same table pointer appears from more than one `source_global` or more than one target.

Promote it beyond a research candidate only after a second isolated capture on the same
binary reproduces the same table pointer or a static cross-reference validates the global.

Reject the candidate when any of these occur:

- `matched_clues` is less than `3/3`.
- Index `0` does not preview as `None`.
- `ClientMessage` and `ServerChat` are swapped, empty, truncated, or unrelated strings.
- Counts are implausible, negative, or inconsistent with the scanner score.
- The table pointer appears only once and is tied to a single chat static without repeated
  evidence.

## UObject Score Triage

Use `UObject validation` only to rank candidate globals:

- Prioritize `score=5/6` or `score=6/6` candidates that repeat across targets or delayed
  probes.
- Treat lower scores as weak evidence unless they accompany an exact `GNames` match.
- Do not accept `GObjects`, `UFunction`, or parameter offsets from this score alone.

## Rollback

After the isolated capture, restore the baseline by disabling the scanner and keeping
plugins disabled until the log has been reviewed:

```bash
unset OBELISK_ENABLE_REFLECTION_SCANNER
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_PE_TRACE_LIMIT=0
./arkserver restart
```

If marker files were used on the isolated instance:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/disable-plugins
./arkserver restart
```

Do not apply these marker changes to the active development server as part of this runbook.

## Result

This turn prepared the capture and later added a passive log analyzer under
`scripts/analyze_reflectionscanner_capture.py`. No server was restarted and no marker files
were changed.

## Next Steps

1. Run the capture on an isolated/debug instance with the required flags above.
2. Paste only the relevant scanner lines into a follow-up research note.
3. If `matched_clues=3/3` repeats, add a dedicated static global reference check before
   accepting any `GNames` offset.
