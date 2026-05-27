# Static FName Root Sampling

## Objective

Replace fixed clue-only static-root validation with a bounded sampler that can test the
actual `UObject.NamePrivate.ComparisonIndex` values observed during ReflectionScanner
runs.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-27
- Runtime safety: opt-in only; no server was touched while implementing this change.

## Hypothesis

The fixed clue indices `0`, `9619`, and `9622` are not reliable enough for the current
ARK binary. A better next probe is to keep the static root slot explicit, then sample the
indices already found in plausible `UObject` candidates and compare the decoded name with
the target string that led us to the object.

## Method

`ReflectionScanner` now supports:

```text
OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x...
OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1
```

When sampling is enabled, the scanner samples only already discovered `UObject`
candidates with validation score `>= 4`. Each sample reads a legacy indirect
`GNames`-style entry by `NamePrivate.ComparisonIndex`, validates `entry_header >> 1`, and
logs one bounded evidence row:

```text
[ReflectionScanner] StaticFNameRoot FName sample: slot=0x... table=... target=<target> source_global=0x... object=<ptr> index=<n> header_index_ok=<true|false> name='<name>' status=<match|mismatch|reject> reason=<reason> num_elements=<n> num_chunks=<n>
```

If sampling is not enabled, the existing fixed static-root probe and delayed retry remain
the behavior for `OBELISK_REFLECTION_STATIC_FNAME_ROOTS`.

## Evidence

The analyzer now parses these sample rows, emits them in JSON, and records:

- `static_fname_root_sample_count`
- `static_fname_root_sample_status_counts`
- `static_fname_root_sample_reason_counts`
- `static_fname_root_sample_target_counts`

Human output includes a short sample summary. `--strict` intentionally does not pass from
samples alone.

## Result

This is a research workflow improvement, not an accepted `GNames` solution. Samples can
show whether a candidate static root resolves observed object name indices, but promotion
still requires stronger evidence and follow-up validation.

## Risks

- Sampling must stay isolated/debug-only with ReflectionScanner.
- A sample `match` is not enough to promote an offset; it may still be a coincidental or
partial structure match.
- The static root slot remains binary-hash-specific research evidence.

## Next Steps

- Run this only on an isolated/debug ARK instance.
- Capture copied logs with `OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1`.
- Analyze with `scripts/analyze_reflectionscanner_capture.py --json`.
- Promote only after repeated samples, no reject markers, and independent static or
second-capture validation.
