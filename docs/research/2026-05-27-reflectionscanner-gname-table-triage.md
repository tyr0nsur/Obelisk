# ReflectionScanner GNames Table Triage

## Objective

Improve offline analysis for `FName -> string` / `GNames` research without enabling live
server probes or accepting offsets from weak evidence.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Scope: offline analyzer and tests only.
- Server state: not touched.
- Native exec probes: not used.

## Hypothesis

A future isolated `ReflectionScanner` capture is easier to review if the analyzer groups
`FName indirect-table probe` rows by table pointer and records explicit accept/reject
reasons instead of relying only on per-line strict pass/fail output.

## Method

Updated `scripts/analyze_reflectionscanner_capture.py` to emit a
`gname_table_candidates` section in both JSON and human output. The analyzer now groups
FName probe rows by `table`, counts research-grade exact hits, records distinct
`source_global` and target evidence, and labels each table as:

- `research-candidate` when an exact clue match repeats through distinct source globals or
  distinct targets.
- `rejected` when the table is single-source only, has partial clue matches, preview
  mismatches, or implausible counts.

## Evidence

Validation:

```bash
python3 -m unittest scripts/test_analyze_reflectionscanner_capture.py
```

Result: 7 tests passed.

The fixture coverage now includes:

- single exact hit rejected as single-source evidence;
- repeated exact hit accepted as a research candidate;
- duplicate exact hit from the same source rejected;
- repeated exact hit by distinct target accepted;
- strict mode rejection when legacy/native probe markers appear;
- implausible counts rejected;
- JSON summary for mixed accepted/rejected table groups.

## Result

The analyzer still remains passive and offline-only. A `research-candidate` status does not
promote a `GNames` offset into runtime code; it only marks a table pointer as worthy of a
second isolated capture or static xref validation.

## Rejected Paths

- No native exec probes were enabled.
- No live server capture was attempted.
- No hardcoded `GNames`, `FNamePool`, `GObjects`, or `UFunction` offset was accepted.

## Risks

- The analyzer can only classify lines that `ReflectionScanner` already logs. It can still
  miss a real `GNames` table if the scanner never reaches the correct global.
- Repeat confirmation inside one capture is not enough to commit an offset.

## Next Steps

1. Use `--json` output after the next isolated capture to compare
   `gname_table_candidates`.
2. Require a second isolated capture or static xref validation before promoting any table.
3. If a strong candidate appears, add an offline static check that explains the global's
   RIP-relative store/reference path before touching runtime decoding.

## Skill Updates Needed

None. Existing UE4 reflection/reversing skills already require offline, gated
ReflectionScanner work and second-source validation.
