# FName Indirect Table Probe

## Objective

Advance `FName`/`GNames` research without enabling live plugins, native exec probes, or
unbounded runtime inspection.

## Environment

- Obelisk commit: `6afb270`
- ARK binary path: `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Map/server: not exercised in this turn
- Plugins: not changed
- Native exec probes: not used

## Hypothesis

ARK's Linux UE4 build may still use an older indirect `GNames` array shape with inline
chunk pointers, followed by `NumElements` and `NumChunks`. Previously observed chat
`FName` indices (`ClientMessage=9619`, `ServerChat=9622`) can be used as bounded clues,
not accepted offsets.

## Method

Added scanner-only candidate logging behind the existing `ReflectionScanner` path:

1. `ue/Reflection.h` now documents a candidate `FNameIndirectArrayProbe` layout:
   128 inline chunk pointers, chunk size 16384, `NumElements` at `0x400`, and
   `NumChunks` at `0x404`.
2. `ue/ReflectionScanner.cpp` now tests already-discovered candidate global values against
   that layout using bounded readable checks.
3. The probe tries to preview entries for index `0` (`None`), `9619` (`ClientMessage`), and
   `9622` (`ServerChat`) from several common legacy `FNameEntry` string offsets and both
   ANSI and UTF-32 encodings.
4. It emits one `FName indirect-table probe` log line only when at least one clue entry is
   readable and the candidate reaches a minimum score.

## Evidence

This turn did not run the scanner against a live server. The implementation is intentionally
passive:

- No new environment gate.
- No hook install.
- No native exec probe activation.
- No gameplay mutation.
- No heap sweep or broad `/proc` scan beyond the existing candidate-global path.

Expected log shape if a candidate is found:

```text
[ReflectionScanner] <target> FName indirect-table probe: source_global=0x<global> table=<ptr> score=<n>/8 readable_clues=<n>/3 matched_clues=<n>/3 num_elements=<n> num_chunks=<n> none='<name>' client_message='<name>' server_chat='<name>'
```

## Result

Code support exists for collecting one more bounded signal during isolated
`ReflectionScanner` captures. A positive score is still only a candidate: it does not prove
`GNames`, the `FNameEntry` header, or the full name table layout.

## Rejected paths

- Did not enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES`.
- Did not add live ChatPlugin discovery or raw ProcessEvent parameter probing.
- Did not accept `9619` or `9622` as stable API identifiers.
- Did not scan arbitrary heap regions for name strings.

## Risks

- Candidate globals derived from chat string initialization may be `UFunction` statics or
  other objects rather than `GNames`.
- The assumed indirect array layout may be wrong for this ARK build.
- `FNameEntry` string offset/encoding is still unknown; previews are a triage aid only.

## Next steps

1. Run `ReflectionScanner` only on an isolated/debug instance with plugins disabled.
2. Capture any `FName indirect-table probe` lines together with existing `UObject`
   validation scores.
3. If a high-scoring table repeats across captures, add a dedicated static search for
   references to that global and validate index `0 == None` plus nearby well-known names.
4. Only after name resolution is reproducible, use it to label `UFunction` candidates and
   continue toward metadata-backed parameter decoding.

## Skill updates needed

No rule change. Existing reflection/reversing skills already require bounded scanner-only
research, isolated validation, and no live native exec probes.
