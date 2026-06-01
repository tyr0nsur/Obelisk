# Inventory Action Redacted Observer Gate

Date: 2026-06-01

## Scope

This note prepares tests and guardrails for the future instance marker
`enable-inventory-action-redacted-observer`. It is candidate-only and internal. It does
not implement runtime C++, wrapper activation, posture-check activation, marker creation,
server execution, Discord/community notice, GitHub action, public SDK work, mutation,
return override, raw parameter exposure, or release readiness.

No server was touched for this note. The marker is not approved for any instance.

## Evidence Boundary

The only planning input is the existing `inventory-action-compact-intake` target set:

- `ShooterPlayerController.ServerRequestInventoryUseItem`
- `ShooterPlayerController.ServerRequestInventoryUseItemWithActor`

The current accepted offline evidence is layout/signature evidence only. It keeps
`ItemId` and `ItemID1` as redacted structs, keeps `InventoryComp` and `anActor` as
redacted UObject references, and treats `AdditionalData` as a copied `int32` candidate
with unknown semantics. That evidence does not promote an Inventory SDK, Items SDK,
item identity, inventory identity, actor identity, lookup, `ResourceHandle`, mutation,
return override, raw params, plugin callbacks, or public ABI.

## Future Gate Shape

The future marker name should be:

```text
state/instances/<instance-id>/enable-inventory-action-redacted-observer
```

The candidate environment names should be scrubbed unless the wrapper has explicitly
accepted the same-instance observer-debug window:

```text
OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER=1
OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256=<supported 64hex>
OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT=<positive bounded integer>
OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT=0
```

The wrapper gate should require all of these on the same instance:

- `OBELISK_WRAPPER_PROFILE=observer-debug`
- `allow-observer-debug-window`
- `allow-experimental-observers`
- `enable-inventory-action-redacted-observer`
- `enable-process-event-hook`
- `disable-plugins`
- supported ARK binary SHA256
- positive bounded log budget
- dispatch budget exactly `0`

Stable profile must fail closed if the marker exists, even when the marker entry is a
directory, symlink, malformed entry, or belongs to a stale observer window. Inherited
`OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_*` environment values must be removed before
launch unless the future gate accepts them.

## Runtime Recognition Contract

The future observer must first prove a no-read/no-budget policy. Disabled gates, missing
profile/window/marker/SHA, unsupported SHA, missing or zero budget, exhausted budget, and
non-target `ProcessEvent` names must avoid metadata reads, parameter reads, budget
reservation, copied output, and retained per-player or per-item state.

If a later implementation exists, recognition must be exact before copying anything:

- exact outer/function name from the two target functions above;
- exact `ParmsSize`, `NumParms`, property order, property class, offset, and size from
  the accepted target set;
- redacted object references only for `InventoryComp` and `anActor`;
- redacted struct fields only for `ItemId` and `ItemID1`;
- copied scalar only for `AdditionalData`, and still candidate-only;
- no `ItemNetID` identity, UObject identity, actor identity, inventory identity, pointer,
  object index, FName/GObjects value, raw buffer, raw params, object name, class name,
  player name, platform id, tribe id, location, or hash of redacted identity values.

Every rejected path must clear copied output. Any attempt to dispatch to plugins or
interpret `AdditionalData` as a stable semantic claim must fail closed until a separate
ABI, privacy, and semantics review exists.

## Pending Wrapper Tests

`scripts/test_linuxgsm_wrapper_markers.sh` now contains an opt-in pending block:

```bash
OBELISK_RUN_PENDING_INVENTORY_ACTION_REDACTED_OBSERVER_TESTS=1 \
  scripts/test_linuxgsm_wrapper_markers.sh
```

These tests are intentionally disabled by default so current wrapper tests keep passing
while no runtime/wrapper implementation exists. If enabled today, they are expected to
fail because the wrapper does not yet know the future marker or env names.

The pending cases assert the intended future fail-closed behavior:

- stable profile refuses `enable-inventory-action-redacted-observer`;
- observer-debug refuses the marker without explicit SHA/log/dispatch budget;
- non-zero dispatch budget fails closed;
- symlink marker entries fail closed;
- inherited future env values are scrubbed when the marker is not accepted.

Do not weaken these pending cases into passing assertions by ignoring the future marker.
The correct promotion path is to implement the wrapper gate later, then enable these cases
as normal tests in the same change that adds the wrapper behavior.

## Non-Claims

This note does not authorize runtime activation, marker edits, restarts, server-backed
validation, scanner/native-exec/ptrace/gcore use, broad `ProcessEvent` tracing, Discord
or community notices, GitHub publication, public Inventory/Items SDK claims, item or
inventory handles, `ResourceHandle`, mutation, return override, public callbacks, raw
params, or production validation.

## Offline Checker

The candidate-only offline gate now has a mechanical checker:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_action_redacted_observer_gate.py \
  --gate-enabled \
  --observer-profile observer-debug \
  --marker allow-observer-debug-window \
  --marker allow-experimental-observers \
  --marker enable-inventory-action-redacted-observer \
  --marker enable-process-event-hook \
  --marker disable-plugins \
  --ark-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --fname-index 2651 \
  --dispatch-budget 0 \
  --json
```

It consumes committed sanitized fixtures through
`scripts/check_inventory_action_fixture_boundary.py`, verifies the exact
`inventory-action-compact-intake` target set and supported binary SHA, and derives the
two accepted target FName indices from the fixture snapshots. The checker accepts only an
offline candidate gate; it still reports `runtime_ready=false`, `public_sdk_ready=false`,
`promotion_ready=false`, and `dispatch_ready=false`.

The dedicated tests cover fail-closed blockers for disabled gate, missing marker,
unsupported SHA, non-target FName, public contract leak, incomplete coverage, redaction
drift, and non-zero dispatch budget. This remains planning hygiene only and does not
authorize any runtime/live work.

## C++ Metadata Recognition

`ue/InventoryReflection` now recognizes the two `inventory-action-compact-intake`
targets by exact metadata only:

- `ShooterPlayerController.ServerRequestInventoryUseItem`
- `ShooterPlayerController.ServerRequestInventoryUseItemWithActor`

All fields for these targets keep `ExposesRange=false`, including `AdditionalData`.
`ProcessEventInventoryReflection` still rejects their FName indices before reading
UFunction memory, so this is an offline recognizer hardening step only. It does not add
runtime observation, dispatch, copied payloads, public ABI, public SDK symbols, identity,
lookup, mutation, or return override.
