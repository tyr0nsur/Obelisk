# Post-RC Target-Set Priorities

Date: 2026-05-30

## Scope

This is an offline planning note for post-`v0.1.0-rc.2` module research. It does not
promote any new public SDK, callback, descriptor, runtime observer, identity surface,
mutation path, or return override.

The current public RC target sets remain:

- `minimal-second-source-intake`
- `structure-observer-intake`
- `item-return-only-policy-slice`
- `chat-message-intake`

Everything below is candidate/internal until it passes copied-data design, privacy,
lifecycle, second-source/static evidence, SDK, and runtime validation gates.

## Current Evidence Shape

Committed base fixtures exist for mission, tribe, dino, buff, transfer, item, inventory,
structure, and chat families under `tests/fixtures/ufunction_snapshots`.

Existing research notes record accepted second-source layout evidence for several
non-public families:

- `mission-compact-intake`: accepted layout evidence with current bool semantics; useful
  for copied bool policy planning, but object refs and arrays remain redacted.
- `dino-compact-intake`: accepted layout evidence for two compact dino functions; useful
  for a fixture-backed internal recognizer only.
- `buff-compact-intake`: accepted layout evidence and existing recognizer tests; runtime
  hooks remain a no-go.
- `transfer-ufunction-intake` and `transfer-scriptstruct`: useful layout evidence but high
  identity and nested-payload risk.
- `tribe-compact-intake`: useful layout evidence, but identity and permissions sensitivity
  make it a later public candidate.

Running `compare_reflection_snapshots.py` without a candidate root against those target
sets correctly reports `missing_candidate_root`; that is only a local diagnostic and does
not invalidate the preserved accepted evidence in the dated research notes.

## Priority Ranking

1. **Mission copied-bool internal bridge**

   Best next fit after item-return because the copied payload can stay scalar-only and
   avoid object identity. Start with internal recognizer and fixture tests. Keep
   `GetPlayerUsableItems` arrays recognition-only.

2. **Dino compact recognizer**

   Useful for future ride/carry policy signals. Keep object fields redacted and do not add
   public Dino SDK, identity, lookup, mutation, or return override.

3. **Buff compact/breadth documentation and recognizer hardening**

   Buff has accepted compact evidence and existing recognizer coverage. Expand only
   offline fixture breadth until redaction and runtime gating are clearer.

4. **Structure build policy focused snapshot**

   `PrimalStructure.IsAllowedToBuild` / `APrimalStructure.IsAllowedToBuild` is high
   demand, but the current committed fixture root lacks the target. First action is a
   sanitized focused snapshot from an approved offline artifact, then a distinct
   second-source compare. Do not add target sets, ABI, descriptors, dispatchers, or public
   docs before that.

5. **Tribe and transfer**

   Keep as later tracks. Both are important for ArkApi-style plugin parity, but they carry
   identity, permissions, upload/download, nested struct, and privacy risks.

## Next Offline Commands

For target sets with existing base fixtures but no selected candidate root in the current
turn, use a candidate root generated from an approved offline artifact:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <approved-offline-ufunction-snapshots> \
  --readiness-report \
  --target-set <target-set> \
  --fail-on-readiness-gaps \
  --json
```

For `IsAllowedToBuild`, use the focused inspector path first rather than adding it to a
manifest or release target set:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core <approved-offline-core> \
  --gobjects 0x595b7e0 \
  --fname-root-slot <verified-fname-root-slot> \
  --outer-exact PrimalStructure \
  --name-exact IsAllowedToBuild \
  --inspection-mode ufunction \
  --snapshot-json \
  --evidence-ark-sha256 <ark-binary-sha256> \
  --evidence-artifact-sha256 <offline-artifact-sha256> \
  --evidence-artifact-kind offline_core \
  --evidence-capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-pack-id> \
  --evidence-obelisk-commit <obelisk-commit>
```

## Non-Claims

This note does not authorize server starts, restarts, marker changes, ReflectionScanner,
ptrace, `gcore`, broad ProcessEvent tracing, Discord updates, GitHub publication, public
module SDKs, raw UE pointer exposure, object identity, lookup, mutation, return override,
or compatibility claims with ArkApi/NextGenPlugins implementations.
