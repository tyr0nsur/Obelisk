# Live Development FName Reject Capture

## Objective

Run a short development-server ReflectionScanner capture with the new opt-in FName reject
logging to determine whether current chat-related globals are plausible `GNames` or
`FNamePool` roots.

## Environment

- Instance: `arkserver`
- Map: `Ragnarok`
- Server role: development/debug server
- Obelisk commit: `8cb3bbe3014c`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Runtime root: `/servidor/ark/obelisk`
- Copied evidence pack:
  `/tmp/obelisk-live-fname-reject-evidence.json`

## Procedure

1. Stopped `arkserver` gracefully.
2. Installed current Obelisk runtime into `/servidor/ark/obelisk` with backups:
   - `libobelisk.so.20260527-041436.bak`
   - `libsubhook.so.20260527-041436.bak`
3. Started `arkserver` once with:

```bash
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_REFLECTION_LOG_FNAME_REJECTS=1
/servidor/ark/arkserver start
```

4. Analyzed `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`.
5. Restarted `arkserver` normally, without ReflectionScanner env flags.

## Runtime State After Capture

Current process environment after the normal restart includes:

- `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1`
- `OBELISK_DISABLE_PLUGINS=1`
- no `OBELISK_ENABLE_REFLECTION_SCANNER`
- no `OBELISK_REFLECTION_LOG_FNAME_REJECTS`

Latest startup log:

```text
ProcessEvent vtable-derived pattern candidates found: 1
ProcessEvent candidate[0] = 0x1d34e20
ProcessEvent absolute x64 hook installed successfully.
ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.
Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.
```

## Analyzer Result

Human summary:

```text
evidence status: inconclusive
candidate globals: 44
delayed globals: 22
UObject validations: 22
FName probes: 0
FName rejects: 22
reject markers: none
FName exact candidates: 0
FName repeat-confirmed candidates: 0
```

Reject reasons:

```text
implausible_num_elements: 21
implausible_num_chunks: 1
```

Top UObject validation rows all scored `6/6`, including `ServerSendChatMessage`,
`ServerChat`, `ClientServerChatMessage`, `ClientChatMessage`, and `ClientMessage`.

## Result

The capture confirms that the current string-reference globals are good UObject/UFunction
leads, but they are not plausible `GNames`/`FNamePool` roots under the current indirect-table
probe. Treating these object pointers as FName tables fails immediately on header counts.

This is useful negative evidence: the next `FName -> string` step should not keep trying to
promote the chat UObject globals into a name table. Continue with either:

- static discovery of the actual name table global from the binary; or
- a broader but still bounded scanner branch for alternate UE4 name storage models.

## Safety Notes

- Native exec probes remained unset.
- Plugins were disabled through the instance marker.
- ReflectionScanner was disabled again after the capture.
- No config files or saves were modified.

