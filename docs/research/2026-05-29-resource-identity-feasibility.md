# Resource Identity Feasibility

## Objective

Define the next research direction for Obelisk `Resource` handles. This note is
candidate-only. It does not add a public API, does not promote `GObjects`, and does not
authorize server access, `ptrace`, `gcore`, runtime observers, marker changes, mutation,
or public exposure of UE4 internals.

The immediate question is not how to name a public handle. It is what must be proven about
`GUObjectArray`, `FUObjectItem`, object lifetime, and privacy before any Obelisk-level
resource identity can be exposed to plugins.

## Current Public Boundary

`GameplayPolicyEvent.resource_kind` is category-only. It currently says only that a copied
policy event is structure-backed. It is not identity, not a lookup key, not a persistent
handle, and not evidence that two events refer to the same game object.

A future `Resource` API must keep the same ABI discipline:

- no `UObject*`, `UClass*`, `UFunction*`, property pointers, or raw parameter buffers;
- no FName index, GObjects index, `InternalIndex`, `FUObjectItem` address, or UE serial in
  the public ABI;
- no pointer-derived identifiers or stable IDs inferred from memory addresses;
- no cross-instance or cross-restart persistence unless a separate game-level identity is
  proven and redacted;
- copied Obelisk-owned payloads only, with owner-token lifecycle and ABI tests.

The likely safe shape, if the evidence is later accepted, is an opaque process-local
Obelisk handle whose backing lookup table is fully internal. Plugins should never be able
to reconstruct the UE object-array coordinate from the handle value.

## Candidate Evidence

Existing docs and tools support a binary-hash-scoped `GUObjectArray` research candidate:

- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Candidate root: `0x595b7e0`.
- Candidate fields from primary-core and static evidence:
  - `chunks = base + 0x10` (`0x595b7f0`);
  - `count = base + 0x24` (`0x595b804`);
  - `serial/master serial = base + 0x58` (`0x595b838`);
  - chunk size candidate: `0x10000` entries;
  - `FUObjectItem` stride candidate: `0x10`.
- Primary-core samples round-trip through `InternalIndex`:
  - index `0` resolves to `/Script/CoreUObject`, class `Package`;
  - index `1` resolves to `Object`, class `Class`;
  - reflected `UFunction` targets such as `ServerChat` at index `25447` can be inspected
    through `GObjects[InternalIndex]`.
- `scripts/inspect_core_ufunctions.py` strengthened candidate membership by requiring
  exact `GObjects[InternalIndex]` back-references for target objects, classes, outers, and
  property objects.
- Static preflight on copied artifacts found code-backed xrefs for all expected field
  targets:
  - `gobjects.root`: 3 code-backed xrefs;
  - `gobjects.chunks`: 8016 code-backed xrefs;
  - `gobjects.count`: 5870 code-backed xrefs;
  - `gobjects.serial`: 2 code-backed xrefs.
- Static window `0x1d56970..0x1d56eb0` looks like an object-handle accessor family:
  it bounds-checks indices against count, loads chunks, derives `FUObjectItem` by
  chunk/index math with stride `0x10`, rejects zero serials, and uses `lock xadd` on
  `0x595b838`.

This evidence is useful for internal research only. It is not enough for a public
Resources API.

## What Must Be Known Before Resource Handles

1. `GUObjectArray` root and field contract

   Later same-base static work and two-core reconciliation make the candidate object-array
   contract strong enough for offline enumeration. That evidence still does not promote a
   public/runtime object identity, lookup, or `ResourceHandle` contract.

2. `FUObjectItem` layout and serial semantics

   The candidate layout must currently stay neutral:

   ```text
   FUObjectItem+0x0  UObject* object
   FUObjectItem+0x8  dword/qword under static serial-accessor hypothesis
   FUObjectItem+0xc  unknown dword
   item stride       0x10
   ```

   This must be reconciled against the static handle-accessor window before it is trusted.
   The current strongest static evidence points at `FUObjectItem+0x8` for the serial-backed
   hypothesis while `+0xc` remains unknown. A Resource handle cannot depend on serial checks
   until the exact field and invalid/reuse rules are known.

3. Pointer-to-item membership

   For every candidate resource object observed in a `ProcessEvent` caller or parameter,
   Obelisk must be able to prove:

   - the pointer is a plausible `UObject`;
   - `UObjectBase.InternalIndex` is in bounds;
   - `GObjects[InternalIndex].Object == pointer`;
   - class and outer are also plausible object-array members where required;
   - stale or freed objects fail closed.

   Broad scans from pointer to index are not an acceptance substitute.

4. Lifetime and reuse behavior

   Resource identity needs more than "this pointer is currently in GObjects." We need to
   know when a handle becomes invalid, whether object slots are reused, how serial values
   change on reuse, whether zero serial is always invalid, and whether a ProcessEvent-time
   object can be safely revalidated later outside the hook frame.

5. Scope semantics

   The first acceptable handle, if any, should be process-local and non-persistent. It must
   not imply cross-map, cross-instance, cross-restart, or cluster identity. Those require
   separate game-level identifiers and privacy policy.

6. Resource-kind classification

   Obelisk must classify the internal object as a public resource kind through reflected
   metadata and accepted target evidence, not through address ranges or names alone. For
   structures, this likely starts with exact structure-backed policy targets and class/outer
   membership. Inventory, players, tribes, dinos, and transfers have higher identity and
   privacy risk and should stay blocked.

7. Privacy and capability policy

   A handle that lets plugins correlate events can reveal identity even without raw fields.
   Before exposure, define whether plugins may correlate repeated structure events, for how
   long, under which capability, and whether pin-code, player, tribe, inventory, or location
   relationships remain redacted.

## Exact Blockers

- `GObjects` remains a binary-hash-scoped research candidate, not a runtime-stable
  contract.
- Static promotion is blocked unless redacted field-window evidence proves one coherent
  root/chunks/count/serial field window for the same candidate. Clearing that blocker does
  not promote public identity by itself.
- Static-only evidence has `promotion_gate.ready=false` because runtime globals cannot be
  promoted from xrefs alone.
- The clean second-source core has accepted selected UFunction target sets, but that does
  not promote the global `GUObjectArray` contract or resource identity.
- `FUObjectItem` serial layout and handle serial validation are not yet reconciled well
  enough for handle invalidation.
- Object-array membership proves current reachability, not post-callback lifetime safety.
- `UObject` flag validity semantics remain unproven for public handle revalidation.
- No policy exists yet for process-local handle duration, invalidation, correlation,
  privacy, or capability gating.
- No public ABI tests, SDK consumer tests, lifecycle cleanup tests, or redaction manifest
  exist for Resources.

## Safest Next Validation Step

Use only copied offline artifacts and existing scripts to produce a focused
`GObjects`/`FUObjectItem` identity evidence pack. Do not broaden gameplay modules first.

1. Start with the clean independent core artifact already documented in
   `2026-05-28-second-source-reversing-gap-matrix.md`.
2. Derive or verify that artifact's FName root first. Do not use the primary-core default
   root by accident.
3. Run `scripts/build_core_dump_evidence_pack.py` with explicit artifact-specific inputs:

   ```bash
   python3 scripts/build_core_dump_evidence_pack.py \
     --binary <offline-ShooterGameServer> \
     --core <offline-independent-core> \
     --output-dir <offline-pack> \
     --no-default-candidates \
     --no-default-fname-roots \
     --gobjects-candidate gobjects=0x595b7e0 \
     --fname-root-slot verified_fname_root_slot=<verified-slot> \
     --gobjects-sample-index 0 \
     --gobjects-sample-index 1 \
     --gobjects-sample-index 25447
   ```

4. Review only these facts from the pack:
   - chunks/count are plausible for the candidate root;
   - sampled objects round-trip by `InternalIndex`;
   - class and outer pointers are plausible object-array members;
   - `FUObjectItem+0x8` and `FUObjectItem+0xc` are recorded neutrally and reconciled with
     the static handle-accessor window without assigning serial semantics to `+0xc`;
   - the pack records distinct artifact identity and no protected server paths.

Acceptance of that step would still not expose Resource handles. It would only unblock the
next internal design note: an opaque process-local handle table with explicit invalidation,
redaction, capability, and ABI test requirements.
