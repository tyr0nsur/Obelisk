# Core UFunction Property Chain

## Objective

Inspect chat-related `UFunction` objects from the existing ARK core dump and reconstruct
their legacy UE4 property chains enough to identify bounded `ProcessEvent` parameter
offsets.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Obelisk baseline commit before this tool:
  `0636722 Add core UObject enumeration tooling`

## Method

Added `scripts/inspect_core_ufunctions.py`, an offline-only core inspector that:

- resolves targets by `GObjects` index or object address;
- prints candidate scalar fields for `UObjectBase`, `UStruct`, `UFunction`, and
  `UProperty`;
- resolves pointer slots through `GObjects` and FName-backed `UObject` summaries;
- validates target, class, outer, and property-chain membership through direct
  `GObjects[InternalIndex]` back-references;
- walks the legacy `UStruct.Children +0x38` and `UField.Next +0x28` chain;
- validates property count against `UFunction.NumParms`;
- validates each property `Offset_Internal + ElementSize` against `ParmsSize`;
- reads a candidate enum pointer for `ByteProperty` at `+0x70` and resolves bounded
  enum names through the confirmed FName table;
- labels output as `candidate-only`.

## Candidate Layout

The current core supports these binary-hash-scoped candidates:

| Field | Offset | Evidence |
|---|---:|---|
| `UField::Next` | `+0x28` | Property chains terminate cleanly and preserve owner. |
| `UStruct::SuperStruct` | `+0x30` | Known classes such as `ShooterPlayerController` resolve plausible inheritance. |
| `UStruct::Children` | `+0x38` | Chat functions point to their first property. |
| `UStruct::PropertySize` | `+0x40` | At least as large as reflected parameter footprint. |
| `UStruct::PropertyLink` | `+0x60` | Matches first property for the inspected chat functions. |
| `UFunction::FunctionFlags` | `+0x90` | Chat functions resolve plausible non-zero flags. |
| `UFunction::RepOffset` | `+0x94` | Chat functions show `0xffff`. |
| `UFunction::NumParms` | `+0x96` | Matches observed property-chain length. |
| `UFunction::ParmsSize` | `+0x98` | Bounds all inspected parameter offsets and sizes. |
| `UFunction::ReturnValueOffset` | `+0x9a` | Void chat functions show `0xffff`. |
| `UFunction` native exec pointer candidate | `+0xa8` | Values land in executable core segments. |
| `UProperty::ArrayDim` | `+0x30` | Properties show `1`. |
| `UProperty::ElementSize` | `+0x34` | `StrProperty` shows `0x10`, `BoolProperty` shows `1`, `IntProperty` shows `4`. |
| `UProperty::PropertyFlags` | `+0x38` | Param flags are plausible and repeatable. |
| `UProperty::Offset_Internal` | `+0x4c` | Multi-param functions show offsets such as `0x10`, `0x20`, `0x24`, and `0x28`. |
| `UByteProperty::Enum` candidate | `+0x70` | `ServerSendChatMessage.SendMode` resolves `EChatSendMode` enum names. |

Rejected stale candidates:

- `UFunction::FunctionFlags +0x88`: chat functions have `0` there.
- `UProperty::Offset_Internal +0x44`: multi-param examples stay `0` there while `+0x4c`
  matches parameter layout.

## Chat Function Evidence

Command:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --index 25447 --index 25449 --index 25452 --index 26281 \
  --window-size 0xb8 \
  --max-object-scan 30000
```

Observed parameter chains:

```text
ServerChat:
  NumParms=1 ParmsSize=0x10
  StrProperty MessageText offset=0x0 element_size=0x10

ServerChatTo:
  NumParms=2 ParmsSize=0x20
  StrProperty SteamID offset=0x0 element_size=0x10
  StrProperty MessageText offset=0x10 element_size=0x10

ServerChatToPlayer:
  NumParms=2 ParmsSize=0x20
  StrProperty PlayerName offset=0x0 element_size=0x10
  StrProperty MessageText offset=0x10 element_size=0x10

SendServerChatMessage:
  NumParms=5 ParmsSize=0x2c
  StrProperty MessageText offset=0x0 element_size=0x10
  StructProperty MessageColor offset=0x10 element_size=0x10
  BoolProperty bIsBold offset=0x20 element_size=0x1
  IntProperty ReceiverTeamId offset=0x24 element_size=0x4
  IntProperty ReceiverPlayerID offset=0x28 element_size=0x4

ServerSendChatMessage:
  NumParms=2 ParmsSize=0x11
  StrProperty ChatMessage offset=0x0 element_size=0x10
  ByteProperty SendMode offset=0x10 element_size=0x1
  ByteProperty enum candidate values:
    EChatSendMode::GlobalChat
    EChatSendMode::GlobalTribeChat
    EChatSendMode::LocalChat
    EChatSendMode::AllianceChat
    EChatSendMode::MAX
    EChatSendMode::EChatSendMode_MAX
```

## Result

This promotes chat parameter discovery from raw memory guessing to reflection-backed
offline evidence for this binary hash and captured process.

Later tooling hardening in `2026-05-27-ufunction-membership-backrefs.md` confirmed
`ServerChat` and `SendServerChatMessage` target/class/outer/property membership through
direct `GObjects[InternalIndex]` back-references.

The next runtime implementation should filter `ProcessEvent` by validated `UFunction*`
targets and decode only reflected parameter buffers bounded by `ParmsSize`. For the first
chat decoder, `FString` reads should be attempted only at the reflected offsets above and
must reject unreadable pointers, implausible lengths, or buffers outside the process maps.

## Risks

- This is still evidence from one core capture and one binary hash.
- The exact `FString` layout and ownership rules are not accepted yet.
- Native exec pointers are observed only as code pointers; they are not hook targets.
- Runtime code must not rely on names alone without validating class, owner, and
  parameter-chain shape.

## Next Steps

1. Add a bounded runtime reflection resolver for the accepted candidate offsets, gated by
   binary hash and debug config.
2. Implement a `ProcessEvent` filter that logs only validated chat `UFunction*` calls.
3. Decode `FString` from reflected param offsets in isolated debug mode.
4. Repeat the offline inspector against a second core before making this a public SDK
   contract.
