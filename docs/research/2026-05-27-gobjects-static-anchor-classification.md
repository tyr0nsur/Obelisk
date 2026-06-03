# GObjects Static Anchor Classification

## Objective

Classify the strongest static contexts around the `0x595b7e0` `GUObjectArray`
research-candidate and separate concrete access paths from objdump grouping noise.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Candidate: `0x595b7e0`
- Tooling: `objdump -d -M intel`

## Evidence

Concrete anchors:

```text
0x79ce22: stores immediate 0x595b7e0 into global slot 0x5958128.
0x79ce42: reads count field 0x595b804.
0x79ce4d: reads chunks field 0x595b7f0.
0x79ce60..0x79ce9d: bounded walk over object indices, chunk index, item stride 0x10,
                    stores first non-null item index and item pointer.
```

Classification: lookup/bootstrap cache. This is a strong independent static shape because
it uses `count`, `chunks`, chunk indexing, and `FUObjectItem` stride together.

```text
0x7a27a7: passes 0x595b7e0 as first argument to helper 0x1d474e0.
0x7a27b1..0x7a27c0: registers a destructor-like callback through __cxa_atexit with
                    0x595b7e0 as callback state.
```

Classification: initialization plus destructor registration for the object-array root.

```text
0x81f118: writes zero to 0x595b7e0 in the startup path.
0x81f206: passes 0x595b7e0 to helper 0x1d476e0 later in the same startup path.
```

Classification: startup reset followed by initialization/finalization helper.

Grouped xref caveat:

```text
0x12d1400 group: xrefs=3488 targets=root,chunks,count,serial
sample instructions include 0x1cdb239, 0x1d4a8ef, 0x12d792b, ...
```

This group is not accepted as one decompiler target. The exported/nearest symbol covers a
large address range and merges unrelated references under a misleading label. Treat it as
evidence that many static references exist, but not as a coherent function until narrower
basic-block or local function boundaries are recovered.

## Result

The concrete `0x595b7e0` static evidence now has three useful classifications:

- lookup/bootstrap cache: `0x79ce22` context;
- init/destructor registration: `0x7a27a7` context;
- startup reset/init helper: `0x81f118` and `0x81f206` context.

This is a stronger second static path than raw xref volume. It supports keeping
`0x595b7e0` as the current `GUObjectArray research-candidate` for this binary hash, but it
still does not promote a runtime-stable offset.

`scripts/build_core_dump_evidence_pack.py` now records two safeguards for future packs:

- exact `0x...` immediates in instructions are captured in addition to objdump comment
  targets, so init/helper anchors such as `mov edi,0x595b7e0` are visible in JSON;
- `function_groups` include `first_xref`, `last_xref`, `xref_span_bytes`, and
  `oversized`, plus separate `anchor_groups` built from small instruction windows.

Follow-up hardening added explicit interpretation fields:

- oversized function groups are tagged
  `interpretation=contaminated-nearest-symbol-bucket`,
  `recommended_for_decompile=false`, and include a `reject_reason` pointing readers to
  `anchor_groups` or exact instruction windows;
- non-oversized function groups are tagged `concrete-instruction-window` and
  `recommended_for_decompile=true`;
- anchor groups now record `anchor_span_bytes`, `oversized`, and `interpretation`, so even
  dense local windows can be rejected as `contaminated-anchor-window`.

Validation against the local 1.1GB objdump completed in about 12 seconds and recovered
`13938` xrefs. Large nearest-symbol buckets were marked `oversized=True`, including
`0x886d80`, `0xeaa3a0`, `0x12d1400`, and `0x81dc59`; the concrete `0x648400` neighborhood
containing `0x79ce22`, `0x7a27a7`, and `0x7a27b6` remained non-oversized.

The hardened pass labels the top contaminated groups directly:

```text
0x886d80: xrefs=6300 span=6376614 interpretation=contaminated-nearest-symbol-bucket
0xeaa3a0: xrefs=4013 span=4315714 interpretation=contaminated-nearest-symbol-bucket
0x12d1400: xrefs=3529 span=35999114 interpretation=contaminated-nearest-symbol-bucket
0x81dc59: xrefs=91 span=313717 interpretation=contaminated-nearest-symbol-bucket
0x648400: xrefs=5 span=22932 interpretation=concrete-instruction-window
```

## Risks

- The binary is stripped; exported labels near these addresses should not be treated as
  true function names.
- The `0x12d1400` group demonstrates that function grouping can be contaminated by large
  nearest-symbol ranges.
- Static classification does not prove runtime lifetime safety or offset stability across
  ARK updates.

## Current No-Repeat Checkpoint

Prefer concrete instruction-window evidence around root/chunks/count/serial accesses when
updating research notes, but do not repeat this classification, broad GObjects scans, or
isolated-core capture for the current binary hash. Later notes already preserve the
reviewed no-scan route and second-core reconciliation for `0x595b7e0`.

Reopen classification only for a new binary hash or contradictory artifact evidence.
Stable runtime/public contracts remain blocked by separate promotion gates.
