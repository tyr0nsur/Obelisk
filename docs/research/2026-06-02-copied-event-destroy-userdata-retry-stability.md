# Copied Event DestroyUserData Retry Stability

Date: 2026-06-02

## Result

Copied-event dispatcher owner cleanup is now retry-stable for `DestroyUserData` failures.
If plugin-owned `DestroyUserData` throws during owner cleanup, the dispatcher retains only
the failed subscription outside the dispatchable callback set and reattempts it on the
next `UnregisterCallbacksForOwner(owner)`.

This preserves the runtime contract: cleanup failure propagates to `PluginManager`,
`dlclose` is skipped until cleanup is proven complete, and retained unload retries do not
call `ObeliskPlugin_Shutdown()` again.

## Coverage

Covered dispatcher families:

- `ChatEventDispatcher`
- `StructureEventDispatcher`
- `InventoryPolicyEventDispatcher`
- `ItemReturnEventDispatcher`
- `PlayerPrincipalEventDispatcher`

`PluginManager` did not need a public ABI or function-table change. The internal contract
remains exception-based: `UnregisterCallbacksForOwner(owner)` throws while retained
cleanup has not completed; `0` means no callback cleanup work remained.

## Validation

Offline validation only; no server/runtime operation.

- `cmake --build build --target chat_event_dispatcher_tests structure_event_dispatcher_tests inventory_policy_event_dispatcher_tests item_return_event_dispatcher_tests player_principal_event_dispatcher_tests`
- `ctest --test-dir build --output-on-failure -R '^(ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests|ItemReturnEventDispatcherTests|PlayerPrincipalEventDispatcherTests)$'`
- `cmake --build build --target plugin_manager_tests`
- `ctest --test-dir build --output-on-failure -R '^PluginManagerTests$'`

New regression coverage asserts that a first owner cleanup attempts all copied-event
destructors, retains the one failed `DestroyUserData`, reports retry work on the next
owner cleanup, retries only the failed destructor, and closes the plugin only after that
retry succeeds.
