# Static ServerSendChatMessage Native Exec Evidence

## Objective

Investigate offline whether native exec candidate `0x154a600` is useful for
`ShooterPlayerController.ServerSendChatMessage`, and recover bounded meaning for
`ChatMessage` / `SendMode` without live probes, attach, or server changes.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Obelisk HEAD during this pass: `59ba8ee`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Tools used: `sha256sum`, `file`, `readelf`, `strings`, `objdump`, and existing
  offline core readers under `scripts/`.

## Hypothesis

`0x154a600` is the registered native exec thunk for
`ShooterPlayerController.ServerSendChatMessage`. The reflected params are an
`FString` chat payload at offset `0x0` and a one-byte chat send mode at offset `0x10`.

## Method

Read-only commands:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
file /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -S -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -l -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer

strings -a -tx /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  | rg -i "ServerSendChatMessage|SendServerChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage|ChatMessage|SendMode"

objdump -d -M intel --start-address=0x1369c60 --stop-address=0x1369d60 \
  /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
objdump -d -M intel --start-address=0x154a560 --stop-address=0x154a760 \
  /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer

python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --index 10443 --window-size 0xc0 --max-object-scan 30000
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --object 0x79b62fa23e70 --window-size 0x100 --max-object-scan 30000

python3 - <<'PY'
from pathlib import Path
import struct, sys
sys.path.insert(0, "scripts")
from scan_core_fname_tables import CoreMemory
from enumerate_core_uobjects import resolve_fname
mem = CoreMemory(Path("/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200"))
fname_table = mem.read_ptr(0x5956f30)
enum_addr = 0x79b62f900440
names = mem.read_ptr(enum_addr + 0x40)
count = struct.unpack("<i", mem.read(enum_addr + 0x48, 4))[0]
for i in range(count):
    raw = mem.read(names + i * 8, 8)
    index, number = struct.unpack("<ii", raw)
    print(i, resolve_fname(mem, fname_table, index, number).text)
mem.close()
PY
```

## Evidence

- The ELF is a stripped x86_64 executable. `.text` covers `0x648400..0x3f6170f`, so
  `0x154a600` is inside executable code for this binary.
- `strings` places ASCII `ServerSendChatMessage` at file offset `0x3d638f1`, runtime
  address `0x41638f1`.
- Static registration-like code at `0x1369d01` loads `esi=0x41638f1` and
  `edx=0x154a600`, then calls the same registration helper pattern used by adjacent
  reflected functions.
- Core `UFunction` object index `10443` resolves as:
  - class `Function`, name `ServerSendChatMessage`;
  - outer `ShooterPlayerController`;
  - `FunctionFlags=0x220cc0`;
  - `NumParms=2`, `ParmsSize=0x11`;
  - native exec candidate at `+0xa8 == 0x154a600`;
  - property chain:
    - `StrProperty ChatMessage`, offset `0x0`, element size `0x10`;
    - `ByteProperty SendMode`, offset `0x10`, element size `0x1`.
- The `0x154a600` thunk unpacks a 16-byte value into `[rbp-0x20]`, then a byte into
  `[rbp-0x21]`, advances `FFrame` bookkeeping, and calls a virtual function through
  `this->vtable + 0x1360` with:
  - `rdi = ShooterPlayerController this`;
  - `rsi = &local FString-like 16-byte value`;
  - `edx = zero-extended SendMode byte`.
- The `ByteProperty SendMode` object at `0x79b62fa23e70` has an aligned pointer slot
  at `+0x70` resolving to enum `EChatSendMode`.
- Reading the `EChatSendMode` enum names array from the core gives six entries:
  - value `0`: `EChatSendMode::GlobalChat`
  - value `1`: `EChatSendMode::GlobalTribeChat`
  - value `2`: `EChatSendMode::LocalChat`
  - value `3`: `EChatSendMode::AllianceChat`
  - value `4`: `EChatSendMode::MAX`
  - value `5`: `EChatSendMode::EChatSendMode_MAX`

## Result

`0x154a600` is useful as cross-validation evidence for the reflected
`ServerSendChatMessage` path. It should not be treated as a hook target from this evidence
alone. Its main value is confirming that the metadata-backed param layout matches the
native thunk's decode shape: `FString ChatMessage` followed by one byte `SendMode`.

`SendMode` is not an opaque byte in this core. It is backed by `EChatSendMode`, with
probable runtime values `0=GlobalChat`, `1=GlobalTribeChat`, `2=LocalChat`, and
`3=AllianceChat`. The `MAX` values should be rejected for chat logging/dispatch.

## Rejected Paths

- Do not infer chat text by scanning arbitrary `FString`-looking memory.
- Do not hook or patch `0x154a600`; the ProcessEvent/reflection path remains safer.
- Do not treat `ServerChat*` cheat-manager functions as proof of normal player chat.
- Do not accept `SendMode` values outside the reflected enum range.

## Risks

- The evidence is scoped to binary SHA256
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520` and one core.
- The enum value mapping is read from the core UEnum layout; it still needs an isolated
  runtime capture to prove which value the client sends for each UI chat mode.
- Function flag names are inferred from UE4 conventions; the useful facts here are the
  owner, property chain, native pointer, and thunk decode shape.
- `0x154a600` can change across ARK updates; do not promote it without binary hash and
  registration/prologue validation.

## Next Steps

1. Keep `ServerSendChatMessage` recognition on the existing binary-hash gate and validate
   `UFunction` owner/name/params before decoding.
2. In a confirmed isolated/debug instance, send one message per chat UI mode and capture
   a bounded ProcessEvent chat log showing function name, param ranges, `SendMode` byte,
   and a strictly decoded `ChatMessage` preview.
3. Reject `SendMode >= 4` and any mismatch between reflected enum pointer, property
   offset, and `ParmsSize=0x11`.
4. Re-run `scripts/verify_chat_reflection_constants.py` and this static registration
   check after any ARK binary hash change.

## Skill Updates Needed

None. This reinforces the existing static/core-first workflow and live native-exec probe
ban.
