# Static FName root probe

Historical note: startup and delayed retry probing are no longer the preferred validation
path for static roots. New work should use post-start debug-control probes, offline core
scanner evidence, or bounded live data-mapping scanners before accepting or rejecting a
candidate.

## Objective

Add a bounded runtime probe for static FName/GNames root candidates found by offline
analysis, and teach the analyzer to parse the resulting evidence.

## Environment

- Obelisk commit at implementation time: local work after `97803a6`.
- Target binary candidate from prior static note:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
  with candidate slot `0x5956f30`.
- No live-server capture was run for this note.

## Method

`ReflectionScanner` now accepts explicit slots through:

```text
OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30
```

The probe is dormant unless the env var is set. For each slot it:

- validates that the slot pointer is readable,
- dereferences the slot into a candidate table,
- checks known FName entries for `None`, `ClientMessage`, and `ServerChat`,
- checks that each entry header encodes the expected index,
- logs a `StaticFNameRoot FName static-root probe` only when all checks pass,
- otherwise logs a `StaticFNameRoot FName static-root reject`.

After the startup check, the scanner also retries the same explicit slots every five
seconds for one minute. The retry does not discover new slots and uses the same acceptance
gate; it exists only to distinguish an uninitialized startup slot from a false static
candidate.

The expected accepted log shape is:

```text
[ReflectionScanner] StaticFNameRoot FName static-root probe: slot=0x... table=... score=<n>/9 readable_clues=<n>/3 matched_clues=<n>/3 header_index_ok=<n>/3 num_elements=<n> num_chunks=<n> none='...' client_message='...' server_chat='...'
```

## Analyzer

`scripts/analyze_reflectionscanner_capture.py` now parses static-root probes and rejects.
It records counts in the evidence pack and treats a static-root probe as a
`research-candidate` only when:

- `None`, `ClientMessage`, and `ServerChat` match exactly,
- `header_index_ok=3/3`,
- element/chunk counts are plausible,
- no global reject markers are present.

`--strict` can pass only from repeat-confirmed indirect-table evidence. Static-root probes
are reported as candidate clues, but a single static-root probe stays inconclusive without
independent static validation or a second isolated capture.

## Result

Offline validation passed:

- CMake configure/build
- CTest
- analyzer unit tests
- installed SDK/layout validation
- `git diff --check`

## Risks

- The slot remains binary-hash-specific and unpromoted until an isolated runtime capture
  confirms it.
- This probe assumes the legacy indirect table layout and header/index encoding inferred
  from static analysis. If ARK uses a different FName storage model in this binary, the
  reject reason should be preserved rather than worked around in live code.
- Do not enable this on a shared/live instance as the normal path. Use an isolated debug
  instance or a short controlled dev capture.

## Next steps

- Run an isolated capture with `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`.
- Inspect both startup and delayed retry lines before rejecting a zero startup slot.
- Analyze copied logs with `scripts/analyze_reflectionscanner_capture.py --json`.
- If accepted, add independent static xref evidence before using it for name resolution.
