# ReflectionScanner Analyzer Review

## Objective

Review whether the current `FName` indirect-table probe and offline analyzer can produce
false positives or miss important candidates, and identify concrete improvements for the
next isolated capture.

## Environment

- Obelisk commit: `1870682`
- Runtime/server: not exercised
- Files reviewed: `ReflectionScanner` research notes, analyzer script, and UE4 reflection
  skills

## Findings

The analyzer previously treated an exact `matched_clues=3/3` row with plausible counts as a
`research_candidate` even when the table appeared only once. The runbook requires repeated
evidence before accepting a `GNames` research candidate, so single-hit rows are a false
positive risk.

The analyzer's count plausibility was weaker than the scanner's runtime scoring: it required
`num_elements > 9622` and `num_chunks > 0`, but did not enforce the scanner's
`num_elements < 10000000` and `num_chunks <= 128` bounds.

The scanner only probes already-discovered candidate global values derived from nearby chat
string references and RIP-relative stores. This can miss a real `GNames` table if no scanned
chat target has an initialization path that stores or exposes that table pointer.

The indirect-table layout is only one legacy UE4 shape: 128 inline chunk pointers with
`NumElements` and `NumChunks` at fixed offsets. A build using a different indirect array
layout, compact `FNamePool`, UTF-16 storage, direct entries, or different entry header size
could be missed.

Name preview is intentionally heuristic. It accepts the first printable ANSI or UTF-32 string
found at candidate offsets `0x8`, `0xC`, `0x10`, or `0x14`. This is useful triage, but can
miss valid entries at other offsets and can falsely match unrelated pointer tables that happen
to reference the three clue strings.

## Small Change Made

The offline analyzer now applies the same high-level count bounds as the scanner and exposes a
`repeat_confirmed_candidate` flag. Human output distinguishes exact candidates from
repeat-confirmed candidates, and `--strict` now requires a repeat-confirmed exact candidate.

## Recommended Next Changes

Log the source global address in each `FName indirect-table probe` line, not just the table
pointer and target name. This would let the analyzer require distinct globals or distinct
targets instead of merely counting repeated table strings.

Log which entry offset and encoding matched for each clue, for example
`none_offset=0x10 none_encoding=ansi`. A real table should produce consistent layout metadata
across all clues.

Add one or two extra stable low-index control names after `None`, if known from static
evidence for this binary. Matching only indices `0`, `9619`, and `9622` leaves too much weight
on chat-specific clues.

Add analyzer fixture tests with copied sample lines covering exact single-hit, repeated exact,
bad counts, reject markers, and swapped or truncated names. These can run without server state
and would prevent regression in the acceptance criteria.

After a repeat-confirmed exact candidate appears, do a static cross-reference pass for the
candidate global before using it as a committed offset. The probe should remain a candidate
ranking tool until the binary proves where the global is initialized and read.

## Risks

`repeat_confirmed_candidate` currently means the same table pointer appeared more than once in
the parsed logs. Until probe lines include source global addresses, this is weaker than proving
that independent globals or targets converged on the same table.
