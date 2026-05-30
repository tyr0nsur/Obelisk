# Dispatcher Hook Safety Hardening

Date: 2026-05-29

## Scope

Record the runtime hardening applied after auditing internal event dispatchers that can be
called from the `ProcessEvent` hook path.

## Findings

- `ChatEventDispatcher` snapshotted only callback subscriptions. A reentrant unregister
  could remove and destroy a later callback's user data while the current dispatch snapshot
  still held that stale pointer.
- `StructureEventDispatcher` already had dispatch depth and deferred destroy state, but
  internal dispatch exceptions were rethrown into the hook path.
- `InventoryPolicyEventDispatcher` had already been moved to the fail-closed pattern in
  this integration slice.
- A follow-up audit found that `StructureEventDispatcher` and
  `InventoryPolicyEventDispatcher` invoked callbacks while holding per-dispatcher mutexes.
  Because both families back public `GameplayPolicyEvent`, concurrent structure and
  inventory callbacks could form a cross-dispatcher unregister deadlock.
- The same audit pattern found that `ChatEventDispatcher` still invoked callbacks and
  pending `DestroyUserData` cleanup under its dispatch mutex, and did not participate in
  the shared callback-scope guard.

## Changes

- `ChatEventDispatcher` now snapshots registration ids, checks that each registration is
  still active before invoking it, tracks dispatch depth, and defers `DestroyUserData`
  until the outermost dispatch finishes.
- `ChatEventDispatcher`, `StructureEventDispatcher`, and `InventoryPolicyEventDispatcher`
  now catch setup/internal dispatch exceptions, log when the logger is initialized, and
  return fail-closed instead of rethrowing into `ProcessEvent`.
- `StructureEventDispatcher` and `InventoryPolicyEventDispatcher` now snapshot callbacks
  under mutex, invoke callbacks outside dispatcher mutexes, and use a shared
  `GameplayCallbackScope` so owner-token unregister from a gameplay callback does not wait
  on another gameplay dispatcher. Removed callback user data is still deferred until the
  outermost dispatch finishes; non-callback cleanup still waits for in-flight dispatches
  before returning.
- `ChatEventDispatcher` now follows the same no-callback-under-dispatcher-mutex model and
  uses the shared callback-scope guard. Self-unregister from a chat callback no longer
  waits on dispatch depth, while non-callback owner cleanup still waits for in-flight chat
  dispatch to finish before returning.
- A later ABI/runtime audit briefly narrowed callback-scope detection to the current
  dispatcher family, but the dispatcher lifecycle review found that this can deadlock when
  two gameplay callback families unregister each other concurrently. The current rule is:
  unregister/owner cleanup initiated from any gameplay callback family must not wait for
  dispatcher cleanup, while non-callback owner/plugin cleanup still waits for in-flight
  dispatch and deferred `DestroyUserData` cleanup before returning.
- A follow-up RC API audit found that `ChatMessageEvent` registration still depended on
  process-global capability/dispatcher state. Constructing a later `PluginManager` with
  chat enabled could widen state for a plugin that loaded before chat was advertised.
  `PluginManager` now stores each plugin owner's captured capability snapshot and chat
  dispatcher at init time; owner-token chat registration checks that owner snapshot plus
  the live runtime gate, so later managers cannot widen an already-loaded plugin.
- The same owner-scoping rule now applies to global ProcessEvent callback registration:
  owner-token registration checks the plugin owner's init-time capability snapshot plus
  the live global-callback gate. A later `PluginManager` cannot retroactively authorize
  global callbacks for an already-loaded plugin that did not receive that capability.
- `ChatEventDispatcherTests` includes a reentrant unregister case that removes a later
  snapshot callback and verifies the removed callback is skipped and destroyed after
  dispatch.
- A follow-up lifecycle hardening pass made owner/plugin cleanup wait until both in-flight
  dispatch and deferred `DestroyUserData` cleanup have completed before returning. This
  closes the unload race where callback storage could be removed, dispatch could finish,
  but a deferred destructor could still be running while plugin unload proceeds.
- Inventory copied-policy dispatch now has an additional fail-closed guard: dispatch
  budget is reserved only after copied event construction accepts the full exact
  `PrimalItem.CanUse` or `PrimalItem.AllowRemoteAddToInventory` field sequence, including
  `HasParameterRanges=true`. Metadata-only inventory action targets, wrong outers, wrong
  scalar shape, forged matched attempts, and reader exceptions cannot consume dispatch
  budget or reach callbacks.
- The test-only Mission hook helper now uses the same copied-data posture before any
  runtime wiring exists: copied-bool targets require exact field order/name/offset/size,
  `HasParameterRanges=true`, one-byte bool ranges, and exact bool counts; object/array
  fields reject any forged range. `GetPlayerUsableItems` is limited to metadata-only
  `BoolCount=0`.

## Validation

```bash
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests|ProcessEventChatReflectionTests|ProcessEventStructureReflectionTests|ProcessEventInventoryReflectionTests|PluginManagerTests|AbiLayoutTests|SdkConsumerFixture.*)$'
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_build_redacted_ufunction_signatures.py
python3 scripts/test_validate_offline_artifact_gate.py
git diff --check
```

Result: all listed tests passed locally. The build completed with existing GCC/spdlog
warning noise from bundled fmt, but linked `libobelisk.so` successfully.

Follow-up validation after cross-dispatcher deadlock hardening:

```bash
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests|PluginManagerTests|ProcessEventStructureReflectionTests|ProcessEventInventoryReflectionTests)$'
```

Result: all listed tests passed locally. The build again completed with existing
GCC/spdlog warning noise from bundled fmt.

Second follow-up validation after moving Chat to the shared no-callback-under-mutex
pattern:

```bash
cmake --build build --target chat_event_dispatcher_tests plugin_manager_tests -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(ChatEventDispatcherTests|PluginManagerTests)$'
```

Result: both listed tests passed locally.

Third follow-up validation after changing the callback scope to be dispatcher-family
specific:

```bash
cmake --build build --target plugin_manager_tests chat_event_dispatcher_tests structure_event_dispatcher_tests inventory_policy_event_dispatcher_tests -j2
ctest --test-dir build --output-on-failure -R '^(PluginManagerTests|ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests)$'
```

Result: all listed tests passed locally.

Fourth follow-up validation after owner-scoped chat and global ProcessEvent capability
snapshots:

```bash
cmake --build build --target abi_layout_tests c_abi_layout_tests chat_event_dispatcher_tests plugin_manager_tests sdk_consumer_fixture -j"$(nproc)"
ctest --test-dir build -R 'AbiLayoutTests|CAbiLayoutTests|ChatEventDispatcherTests|PluginManagerTests|SdkConsumer' --output-on-failure
python3 -m unittest scripts/test_analyze_chat_delivery_log.py
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_release_scope_guardrails.py
python3 -m unittest scripts/test_research_doc_guardrails.py scripts/test_secret_guardrails.py
git diff --check
```

Result: all listed tests passed locally. The build emitted existing GCC/spdlog warning
noise from bundled fmt while compiling, but all targets linked and tests passed.

Fifth follow-up validation after deferred-destroy cleanup became part of the owner/plugin
cleanup wait condition:

```bash
cmake --build build --target chat_event_dispatcher_tests inventory_policy_event_dispatcher_tests structure_event_dispatcher_tests process_event_dispatch_tests -j"$(nproc)"
ctest --test-dir build -R '^(ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests|ProcessEventDispatchTests)$' --output-on-failure
```

Result: all listed tests passed locally.

Sixth follow-up validation after cross-family callback cleanup suppression was restored to
avoid callback-to-callback deadlocks:

```bash
cmake --build build -j"$(nproc)"
ctest --test-dir build -R '^(ChatEventDispatcherTests|StructureEventDispatcherTests|InventoryPolicyEventDispatcherTests)$' --output-on-failure
git diff --check -- core/ChatEventDispatcher.cpp core/ChatEventDispatcher.h core/InventoryPolicyEventDispatcher.cpp core/InventoryPolicyEventDispatcher.h core/StructureEventDispatcher.cpp core/StructureEventDispatcher.h tests/core/ChatEventDispatcherTests.cpp tests/core/InventoryPolicyEventDispatcherTests.cpp tests/core/StructureEventDispatcherTests.cpp
```

Result: all listed tests passed locally in the dispatcher lifecycle review. A direct
mixed-family regression test is still desirable if a small shared test seam is added.

Seventh follow-up validation after inventory dispatch-budget and parameter-range
ownership hardening:

```bash
cmake --build build --target process_event_inventory_reflection_tests inventory_policy_event_dispatcher_tests inventory_reflection_tests c_abi_layout_tests -j"$(nproc)"
ctest --test-dir build -R '^(ProcessEventInventoryReflectionTests|InventoryPolicyEventDispatcherTests|InventoryReflectionTests|CAbiLayoutTests)$' --output-on-failure
python3 scripts/test_validate_offline_artifact_gate.py
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_release_scope_guardrails.py
python3 scripts/test_agent_handoff_guardrails.py
python3 scripts/test_research_doc_guardrails.py
```

Result: all listed tests passed locally.

Eighth follow-up validation after mission test-only copied-observation hardening and
inventory reader-exception/builder-before-budget hardening:

```bash
cmake --build build --target process_event_mission_reflection_tests process_event_inventory_reflection_tests inventory_policy_event_dispatcher_tests inventory_reflection_tests c_abi_layout_tests -j"$(nproc)"
ctest --test-dir build -R '^(ProcessEventMissionReflectionTests|ProcessEventInventoryReflectionTests|InventoryPolicyEventDispatcherTests|InventoryReflectionTests|CAbiLayoutTests)$' --output-on-failure
git diff --check -- hooks/ProcessEventMissionReflection.cpp tests/core/ProcessEventMissionReflectionTests.cpp hooks/ProcessEventInventoryReflection.cpp tests/core/ProcessEventInventoryReflectionTests.cpp docs/research/2026-05-29-chat-message-mode-coverage-beta-runbook.md docs/agent-handoff/CURRENT.md
```

Result: all listed tests passed locally.

## Non-Claims

- This is runtime dispatcher hardening only.
- It does not validate live `ChatMessageEvent` delivery on `arkserver` / Ragnarok.
- It does not promote Inventory, StructureEvents, Mission, Dino, Tribe, Transfer, object
  identity, mutation, return override, or `ResourceHandle` public SDK surfaces.
