# ReflectionScanner Candidate Validation

## Objective

Advance `FName`/`GNames`/`GObjects`/`UFunction` research with a small scanner-only change
that improves candidate evidence without enabling ChatPlugin, native exec probes, or live
server behavior.

## Environment

- Workspace: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit observed during this round: `d00899e`
- Date: 2026-05-27
- Runtime servers: not touched
- ChatPlugin live/discovery: not enabled
- Native exec probes: not used

## Hypothesis

Future isolated `ReflectionScanner` captures will be easier to triage if each candidate
global logs a bounded `UObject` shape validation score, and the scanner avoids reading past
the exact range it has checked.

## Method

1. Kept all behavior behind existing scanner gates.
2. Added candidate-only `UObject` validation in `ue/ReflectionScanner.cpp`:
   - canonical user pointer check
   - vtable pointer readability before reading the first entry
   - first vtable entry executable-range check
   - nullable/readable class and outer pointer checks
   - bounded `FName`, object flags, and internal index plausibility checks
3. Replaced unchecked `0x00..0x1F8` executable-field reads with per-field readability
   checks.

## Evidence

- `cmake --build build` completed successfully.
- `git diff --check` completed successfully.
- No `/servidor/ark` paths were touched.
- No `ChatPlugin` behavior was changed.

## Result

`ReflectionScanner` now emits a `UObject validation` line with a `score=.../6` for already
discovered candidate globals. The score is a triage aid only, not proof of `GObjects`,
`GNames`, or a stable `UFunction` layout.

The executable-field scan is also safer for research captures: it stops when the next
pointer-sized field is not readable instead of assuming the whole `0x200` candidate window
is readable after an earlier `0x80` check.

## Rejected Paths

- Did not enable or extend ChatPlugin discovery.
- Did not activate native exec probes.
- Did not touch live server state.
- Did not hardcode observed chat FName indices as stable contracts.
- Did not accept any `GObjects`, `GNames`, or `UFunction` offset from heuristics alone.

## Risks

- The validation score uses heuristics and broad plausibility bounds. It should only help
  rank candidates for the next isolated capture.
- `Memory::IsReadable` is now maps-backed, but scanner output must still be cross-validated
  against names and object enumeration before accepting metadata offsets.
- A high-scoring object shape can still be a false positive without `GNames`/`GObjects`
  confirmation.

## Next Steps

1. Run `ReflectionScanner` only on an isolated/debug instance with plugins disabled.
2. Compare validation scores across repeated candidates and prioritize globals whose
   candidate values produce stable vtable/class/name shapes.
3. Use high-scoring repeated object shapes to design a guarded `GUObjectArray` candidate
   scan.
4. Resolve names through `GNames`/`FNamePool` before using any FName index as more than a
   hint.

## Skill Updates Needed

No skill rule changed. Existing reflection/reversing rules already require isolated scanner
captures, metadata-backed decoding, and no live ChatPlugin/native exec experiments.
