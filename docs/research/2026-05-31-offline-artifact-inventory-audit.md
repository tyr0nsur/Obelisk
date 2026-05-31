# Offline Artifact Inventory Audit

Date: 2026-05-31

This note records the current local artifact-root audit for
`/home/flowcommunity-ark/obelisk-artifacts`. It is a routing aid only. It does not
promote public SDK APIs, runtime readiness, object identity, lookup, mutation, return
override, command/chat replies, permissions, player identity, or cross-binary support.

## Consumable Now

Current normalized artifact-pack roots that can be consumed for internal planning or
evidence review only:

- `item-return-only-policy-slice-20260530T072255Z`
- `item-return-only-second-source-20260530T084918Z`
- `mission-copied-bool-policy-slice-20260530T072912Z`
- `mission-copied-bool-tail-policy-slice-20260530T090211Z`
- `structure-aggregate-census-policy-slice-20260531T034715Z`
- `structure-return-only-policy-slice-20260530T093002Z`
- `transfer-baccept-only-policy-slice-20260530T073308Z`
- `transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack`

Current accepted consume-gate roots:

- `rc-minimal-redacted-signatures-strict-20260530T000000Z`: strict redacted
  signature evidence only.
- `item-return-only-bool-tail-refresh-20260530T172552Z`: item return-only bool-tail
  layout evidence only.
- `static-global-field-window-strict-20260531T040157Z`: static field-window evidence
  only.

`offline-binaries` is reproducibility input, not evidence by itself.

## Limits

- `layout-only`: usable to compare shapes, offsets, bool tails, or field windows for the
  named target set only.
- `evidence-only`: usable as supporting proof for a narrow internal claim; it is not a
  public SDK, runtime, identity, lookup, mutation, or return-override claim.
- `consume-only`: accepted for offline consumption or planning; promote mode/public
  claims remain blocked unless a separate promotion gate accepts them.

Legacy or candidate-blocked roots such as old ResourceHandle/UObject packs, legacy
minimal intake, and structure nonpin scalar slices should not be treated as current
normalized packs. Cite their dated research notes or regenerate current artifacts before
using them as active evidence.

## Current Blockers

Player identity is still blocked before focal planning. The artifact root has the
matching offline `ShooterGameServer` binary, but no paired non-protected core input, no
complete `obelisk.core-dump-evidence-pack.v1`, and no accepted
`obelisk.reflection-inventory-pack.v1` for `players-identity-lifecycle-intake`.

Command/chat response orientation is not an artifact gate. The static checker reports
candidate-only orientation for `obelisk.command_chat_response_path.v1` with
`not_artifact_gate=true`; it does not prove replies, send-chat, command routing,
identity, permissions, runtime readiness, copied response ownership, or public SDK
promotion.

## Checks

- `normalize_artifact_pack.py --check --json` accepted the normalized roots listed
  above and rejected legacy schemas as unsupported.
- `check_reflection_inventory_pack_readiness.py --root` reported
  `missing_reflection_inventory_pack`.
- `check_player_identity_first_evidence_readiness.py --artifact-root --json` reported
  `non_protected_core_input_missing`.
- `check_command_chat_response_static_orientation.py --json` reported valid
  candidate-only orientation and `not_artifact_gate=true`.
