# FString Layout Candidate

## Objective

Determine the safest candidate layout for decoding reflected ARK Linux `StrProperty`
parameters after `UFunction` and property-chain validation.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`

## Candidate Layout

For this build, the strongest candidate is:

```cpp
struct FString {
    TCHAR* Data;      // 8 bytes
    int32_t ArrayNum; // number of TCHAR values, including trailing NUL
    int32_t ArrayMax;
};

// TCHAR appears to be UTF-32 little-endian, 4 bytes per character.
```

This matches the reflected `StrProperty` `ElementSize == 0x10` observed for chat params.

## Evidence

`StrProperty` parameters in chat functions are 16-byte values:

```text
ServerChat.MessageText offset=0x0 size=0x10
ServerChatTo.SteamID offset=0x0 size=0x10
ServerChatTo.MessageText offset=0x10 size=0x10
ServerChatToPlayer.PlayerName offset=0x0 size=0x10
ServerChatToPlayer.MessageText offset=0x10 size=0x10
```

ELF static evidence:

- `.rodata 0x426a9d8` contains UTF-32LE `ServerChat`.
- `.rodata 0x416f7f7` contains ASCII `ServerChat` for registration/reflection naming.
- A bounded xref path reaches code at `0x1c892d0`; the loop reads `DWORD PTR [r15]` and
  advances by four bytes, which matches 32-bit `TCHAR` consumption.

Core evidence:

```text
header 0x2f43da00:
  Data=0x2f4a2a20 ArrayNum=11 ArrayMax=11

buffer 0x2f4a2a20:
  UTF-32LE "PlayerName\0"
```

Additional adjacent headers decode as UTF-32LE strings:

```text
0x2f43d9c0 data=0x2f448680 num=13 max=13 utf32="GraphLiteral"
0x2f43d9d0 data=0x2f4486c0 num=14 max=14 utf32="PlayerRootLoc"
0x2f43d9e0 data=0x2f4a29c0 num=10 max=10 utf32="656511216"
0x2f43da00 data=0x2f4a2a20 num=11 max=11 utf32="PlayerName"
```

The same buffers interpreted as UTF-16 or ANSI terminate after the first character because
the second byte/word is zero. That rejects ANSI and UTF-16 for these examples.

## Decoder Rules

Only attempt decoding after `UFunction`, `UProperty`, and `ParmsSize` validation succeeds.

1. Read exactly 16 bytes as `<uint64 Data, int32 ArrayNum, int32 ArrayMax>`.
2. Accept empty string only as `Data=null`, `ArrayNum=0`, `ArrayMax=0`.
3. Reject non-canonical or unreadable `Data`.
4. Reject `ArrayNum <= 0`, `ArrayNum > maxChars`, `ArrayMax < ArrayNum`, or
   `ArrayMax > maxChars * 2`.
5. Reject `ArrayNum * 4` overflow.
6. Read `ArrayNum * 4` bytes from `Data`.
7. Require the final `uint32_t` codepoint to be `0`.
8. Decode the first `ArrayNum - 1` codepoints as UTF-32LE.
9. Reject codepoints above `0x10ffff` and surrogate-range values.
10. Do not cache `Data`; it is borrowed memory from the current `ProcessEvent` frame.

Initial runtime limit: `maxChars=512` for chat logging. Keep `2048` only as an absolute
upper bound for generic future helpers.

## Rejected

- ASCII `.rodata` and FName entries do not prove `FString`; they belong to reflection
  registration/name paths.
- UTF-16 and ANSI do not match the core buffers above.
- This is not yet public ABI evidence. It should be repeated with a real runtime chat
  capture before becoming stable SDK behavior.

## Next Steps

1. Add a UTF-32 `FString` decoder helper with synthetic tests.
2. Keep it internal and gated behind validated chat reflection.
3. Use it only on reflected `StrProperty` parameter ranges.
4. After one live chat capture confirms the layout, consider exposing decoded chat through
   an internal event path.
