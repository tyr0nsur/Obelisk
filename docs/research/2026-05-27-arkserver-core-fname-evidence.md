# Arkserver Core FName Evidence

## Objective

Use an operator-authorized Linux core dump from `arkserver` / Ragnarok to validate the
current static FName root candidate and correct ReflectionScanner clue indices.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Commit deployed for dump: `9f320a0`
- Server: `arkserver` / Ragnarok, explicitly designated as Obelisk debug harness
- Runtime posture for dump: `OBELISK_DEBUG_ALLOW_PTRACE=1`, plugins disabled,
  ProcessEvent hook enabled, ReflectionScanner disabled
- Stable posture after dump: restored; `scripts/check_obelisk_server_posture.sh
  --expect-stable` passed for PID `2906605`
- Core dump directory:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z`
- Core evidence pack:
  `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`

## Method

`gcore` could not attach to the already-running process while Yama `ptrace_scope=1` was
active. Obelisk gained an explicit debug gate:

```text
OBELISK_DEBUG_ALLOW_PTRACE=1
```

When set at process startup, Obelisk calls `prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY)`.
The per-instance marker used for this dump was:

```text
/servidor/ark/obelisk/state/instances/arkserver/allow-ptrace
```

After the dump, that marker was removed and `arkserver` was restarted back to stable
posture.

The dump was captured with:

```bash
gcore -o /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z 2902200
```

The offline pack was generated with:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --output-dir /servidor/ark/obelisk/dumps/core-pack-20260527T031311Z \
  --skip-core-sha256
```

## Evidence

GDB confirmed the static slot and table shape:

```text
0x5956f30 -> 0x2ae5c660
table + 0x800 num_elements = 0x4516e
table + 0x804 num_chunks = 0x12
chunk0 = 0x79b64ac26000
entry0 = 0x2ae60000
entry0 + 0x10 = "None"
```

Known FName indices from the core:

```text
0      -> None
1865   -> ClientChatMessage
1984   -> ClientServerChatMessage
2697   -> ServerSendChatMessage
4884   -> ClientMessage
9619   -> ServerChat
9620   -> ServerChatTo
9621   -> ServerChatToPlayer
9622   -> SetActiveMissionDebugFlags
```

This explains the earlier failed static-root probe: the scanner clues used
`9619 -> ClientMessage` and `9622 -> ServerChat`, but the core proves those indices are
wrong for the current binary/process.

## Result

`0x5956f30` is now a strong FName/GNames research candidate for this exact ARK Linux binary
hash. It is not yet a stable runtime contract across updates.

ReflectionScanner clue indices were corrected to:

```text
0    -> None
4884 -> ClientMessage
9619 -> ServerChat
```

## Risks

- This evidence is from one process image and one binary hash.
- A future ARK update can move the global slot or change table contents.
- The core contains sensitive server/player memory and must not be committed.
- `OBELISK_DEBUG_ALLOW_PTRACE=1` is a temporary debug posture and must not remain enabled
  during stable operation.

## Next Steps

1. Build and deploy the corrected ReflectionScanner.
2. Run a short scanner capture with
   `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30` on the debug harness.
3. Require analyzer strict success plus static xref evidence before promoting runtime
   name-resolution code.
4. Use this FName resolver evidence as the base for `GObjects` discovery.
