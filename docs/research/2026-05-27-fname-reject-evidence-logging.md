# FName Reject Evidence Logging

## Objective

Reduce blind spots in `GNames`/`FNamePool` research when the bounded FName indirect-table
probe finds candidate globals but rejects them before emitting a positive probe line.

## Environment

- Obelisk commit under test: pending at time of writing.
- Runtime path: `ue/ReflectionScanner.cpp`.
- Offline analyzer: `scripts/analyze_reflectionscanner_capture.py`.
- Server state: no ARK server state was modified for this change.

## Change

`ReflectionScanner` now supports an extra opt-in diagnostic flag:

```bash
OBELISK_REFLECTION_LOG_FNAME_REJECTS=1
```

When the existing FName indirect-table probe rejects an already-discovered candidate, it can
emit:

```text
[ReflectionScanner] <target> FName indirect-table reject: source_global=0x<global> table=<ptr> reason=<reason> readable_clues=<n>/3 matched_clues=<n>/3 num_elements=<n> num_chunks=<n> none='<name>' client_message='<name>' server_chat='<name>'
```

Reasons currently include:

- `unreadable_table_header`
- `implausible_num_elements`
- `implausible_num_chunks`
- `unreadable_chunk_pointer`
- `unreadable_entry_pointer`
- `empty_entry_preview`
- `preview_mismatch`
- `insufficient_score`

The flag does not broaden the scan and does not install hooks. It only makes rejection
reasons visible for the same bounded `None`, `ClientMessage`, and `ServerChat` clues.

## Analyzer Support

The passive analyzer now parses `FName indirect-table reject` lines and records:

- `fname_rejects`
- `evidence_pack.fname_reject_count`
- `evidence_pack.fname_reject_reason_counts`

Rejects remain diagnostic only. They do not satisfy `--strict`, do not promote a table to
`research-candidate`, and do not replace repeat-confirmed `matched_clues=3/3` evidence.

## Recommended Capture

For the next isolated debug run, keep the normal gates and add reject logging:

```bash
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_REFLECTION_LOG_FNAME_REJECTS=1
```

Then analyze copied logs:

```bash
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/isolated/Obelisk.log
```

If reject reasons cluster around `unreadable_chunk_pointer` or `empty_entry_preview`, the
next research focus should be alternate UE4 FName storage models or entry string offsets.
If reasons cluster around `preview_mismatch`, prioritize validating whether the observed
indices are binary/version-specific clues or whether the candidate table is a different
global entirely.

## Validation

- `cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo`
- `cmake --build build -j$(nproc)`
- `ctest --test-dir build --output-on-failure`
- `python3 -m unittest scripts/test_analyze_reflectionscanner_capture.py`
- `scripts/test_install_obelisk_layout.sh /tmp/obelisk-fname-reject-layout`
- `git diff --check`

