# Inventory Reflection Metadata Hardening

## Summary

Inventory copied-bool dispatch was hardened to require exact UE4 metadata before
constructing internal `GameplayPolicyEvent` inventory signals.

## Evidence

- `PrimalItem.CanUse`
  - Function class object index: `518`
  - Outer `PrimalItem` object index: `17`
  - `bIgnoreCooldown`: `BoolProperty` object index `532`, flags `0x1040000280`
  - `ReturnValue`: `BoolProperty` object index `532`, flags `0x1040000780`
- `PrimalItem.AllowRemoteAddToInventory`
  - Function class object index: `518`
  - Outer `PrimalItem` object index: `17`
  - `invComp`: `ObjectProperty` object index `534`, flags `0x1044080280`
  - `ByPC`: `ObjectProperty` object index `534`, flags `0x1040000280`
  - `bRequestedByPlayer`: `BoolProperty` object index `532`, flags `0x1040000280`
  - `ReturnValue`: `BoolProperty` object index `532`, flags `0x1040000780`

Source snapshots:

- `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/PrimalItem.CanUse.snapshot.json`
- `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/PrimalItem.AllowRemoteAddToInventory.snapshot.json`

## Boundary

This is internal hardening only. It does not add a public Inventory SDK, ABI fields,
object/item identity, raw params, mutation, return override, `ResourceHandle`, `ItemId`,
or `AdditionalData`.

## Validation

```text
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(InventoryReflectionTests|ProcessEventInventoryReflectionTests|InventoryPolicyEventDispatcherTests|AbiLayoutTests|CAbiLayoutTests)$'
ctest --test-dir build --output-on-failure -R '^(SdkConsumerFixture|SdkConsumerFixtureCAbiPlugin|SdkConsumerFixtureCAbiPluginShortApiSkipsAppendedCallbacks|SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithoutCapability)$'
```

All listed tests passed locally.
