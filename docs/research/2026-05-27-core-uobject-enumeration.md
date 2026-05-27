# Core UObject Enumeration

## Objective

Use the confirmed core FName table and `GUObjectArray` research-candidate to enumerate
UObjects offline and find real `UFunction` objects for chat-related names.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- FName root slot in this core: `0x5956f30 -> 0x2ae5c660`
- `GUObjectArray` research-candidate: `0x595b7e0`
- Object chunks: `0x2c6f2cc0`
- Object count: `1243796`
- `FUObjectItem` stride confirmed by core samples and static xrefs: `0x10`

## Method

Added `scripts/enumerate_core_uobjects.py`, an offline-only core reader that:

- reuses the ELF core memory reader from `scripts/scan_core_fname_tables.py`;
- reads `GUObjectArray` chunks from `0x595b7e0 + 0x10`;
- walks bounded object indices;
- resolves `UObjectBase` fields:
  - `ObjectFlags` at `+0x08`;
  - `InternalIndex` at `+0x0c`;
  - `ClassPrivate` at `+0x10`;
  - `NamePrivate.ComparisonIndex` at `+0x18`;
  - `NamePrivate.Number` at `+0x1c`;
  - `OuterPrivate` at `+0x20`;
- resolves object and class names through the confirmed FName table;
- filters by object name and class name.

## Evidence

Command:

```bash
python3 scripts/enumerate_core_uobjects.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-objects 30000 \
  --class-contains Function \
  --name-contains ServerChat
```

Output summary:

```text
idx=9768  class='Function' name='ClientServerChatDirectMessage' internal_index=9768 match=True
idx=9772  class='Function' name='ClientServerChatMessage' internal_index=9772 match=True
idx=25447 class='Function' name='ServerChat' internal_index=25447 match=True
idx=25449 class='Function' name='ServerChatTo' internal_index=25449 match=True
idx=25452 class='Function' name='ServerChatToPlayer' internal_index=25452 match=True
idx=26240 class='Function' name='OnServerChatMessage__DelegateSignature' internal_index=26240 match=True
idx=26281 class='Function' name='SendServerChatMessage' internal_index=26281 match=True
```

Full local artifacts:

- `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z/core-uobjects-chat-250k.txt`
- `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z/core-uobjects-serverchat-functions.txt`
- `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z/core-uobjects-serverchat-functions.json`

## Result

This promotes offline `GObjects -> UObject name/class` enumeration to a working research
tool for this core and binary hash.

Chat interception should now target reflected `UFunction` evidence, not raw ProcessEvent
param scanning. The next concrete targets are:

- `ServerChat` at object `0x79b62fc1cd40`, object index `25447`;
- `ServerChatTo` at object `0x79b62fc1ce70`, object index `25449`;
- `ServerChatToPlayer` at object `0x79b62fc1d010`, object index `25452`;
- `ServerSendChatMessage` at object `0x79b62fa23db0`, object index `10443`;
- `ClientChatMessage` at object `0x79b62fa03800`, object index `9548`.

## Risks

- This is still core-specific evidence, not a runtime-stable offset contract.
- `UFunction` metadata offsets and property chains now have candidate-only offline
  evidence in `2026-05-27-core-ufunction-property-chain.md`, but they are not accepted as
  runtime-stable or SDK-visible contracts yet.
- The enumerator currently targets the legacy FName table shape confirmed in this core.
- Name/class matches are necessary but not sufficient; each target needs metadata and
  property-chain validation before any runtime chat decoder.

## Next Steps

Completed/superseded by `scripts/inspect_core_ufunctions.py` and
`2026-05-27-core-ufunction-property-chain.md`:

1. Add an offline `UFunction` inspection pass for the function objects above.
2. Inspect candidate windows for `FunctionFlags`, `NumParms`, `ParmsSize`,
   `ReturnValueOffset`, and property/children chain roots.
3. Resolve property object names/classes through the same FName/GObjects path.

Remaining:

1. Strengthen `ClassPrivate`/`OuterPrivate` back-reference validation for UObject and
   property objects.
2. Repeat the inspector against a second core before promoting any runtime-stable contract.
3. Keep runtime `ProcessEvent` recognition gated to validated `UFunction*` targets and
   isolated debug windows.
