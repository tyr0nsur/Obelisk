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

## Risks

- The binary is stripped; exported labels near these addresses should not be treated as
  true function names.
- The `0x12d1400` group demonstrates that function grouping can be contaminated by large
  nearest-symbol ranges.
- Static classification does not prove runtime lifetime safety or offset stability across
  ARK updates.

## Next Steps

1. Prefer concrete instruction-window evidence around root/chunks/count/serial accesses
   when updating research notes.
2. Repeat the same classification after a second isolated core or binary update before
   promoting stable contracts.
