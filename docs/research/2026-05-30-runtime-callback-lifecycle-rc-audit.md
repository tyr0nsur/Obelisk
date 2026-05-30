# Runtime Callback Lifecycle RC Audit

## Result

The RC runtime callback/lifecycle slice is ready for local checkpointing after the
`ProcessEvent` detour exception guard.

Verified claims:

- gameplay/chat callback dispatchers keep process-lifetime state;
- plugin owner cleanup removes registrations on init failure, shutdown, and unload;
- cleanup waits for in-flight dispatch outside callback context;
- cleanup initiated from gameplay callback context avoids cross-family deadlocks;
- public `GameplayPolicyEvent` and `ChatMessageEvent` callbacks remain copied event paths;
- internal detour failures are caught at the hook boundary, and the original
  `ProcessEvent` path is attempted once if it had not already run.

## Non-Claims

This is static/build/test evidence only. It does not authorize server starts, restarts,
runtime observation, broad `ProcessEvent` tracing, mutation, return override, public
`CallProcessEvent`, public Inventory/Structure/Mission/Item/Transfer SDKs, or
`ResourceHandle` promotion.

## Validation

Commands used for the scoped audit:

```bash
cmake --build build --target obelisk chat_event_dispatcher_tests \
  structure_event_dispatcher_tests inventory_policy_event_dispatcher_tests \
  plugin_manager_tests process_event_chat_reflection_tests \
  process_event_inventory_reflection_tests process_event_structure_reflection_tests \
  -j"$(nproc)"

ctest --test-dir build --output-on-failure \
  -R '^(ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests|PluginManagerTests|ProcessEventChatReflectionTests|ProcessEventInventoryReflectionTests|ProcessEventStructureReflectionTests)$'
```

Operational guardrails for observer debug routing were checked offline only:

```bash
python3 scripts/test_obelisk_cli.py
scripts/test_check_obelisk_server_posture.sh
scripts/test_linuxgsm_wrapper_markers.sh
```
