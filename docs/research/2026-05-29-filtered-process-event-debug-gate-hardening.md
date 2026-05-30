# Filtered ProcessEvent Debug Gate Hardening

## Context

An internal module-boundary audit found that public filtered `ProcessEvent` callbacks were
still available in stable plugin posture. Although they are scoped by `FName` index and are
not a module SDK, the callback ABI receives borrowed `caller`, `function`, and `parms`
pointers. A plugin that knows internal module FName indices could observe raw UE parameter
memory and potentially mutate it.

That conflicted with the RC boundary for copied `GameplayPolicyEvent` and
`ChatMessageEvent` payloads, where identity, raw params, mutation, and return override stay
blocked.

## Change

Filtered raw `ProcessEvent` callback registration now requires a dedicated debug gate:

```text
OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1
state/instances/<instance-id>/allow-filtered-process-event-callbacks
OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS
```

`OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES` is advertised only when filtered
or global raw `ProcessEvent` callback gates are active. Stable plugin code should use
copied Obelisk-level events instead of raw `ProcessEvent` callbacks.

## Non-Claims

- This does not remove the ABI v1 raw callback slots.
- This does not promote mutation, return override, raw UE params, FName/GObjects indices,
  or object identity.
- This does not change `GameplayPolicyEvent` or `ChatMessageEvent` copied payload scope.
- This does not authorize server restarts or runtime observation.

## Validation

```bash
cmake --build build --target plugin_manager_tests c_abi_layout_tests abi_layout_tests oBaseEvents sdk_consumer_fixture sdk_consumer_c_abi_plugin sdk_consumer_minimal_plugin sdk_consumer_minimal_no_shutdown_plugin -j2
ctest --test-dir build -R '^(PluginManagerTests|AbiLayoutTests|CAbiLayoutTests|SdkConsumer)' --output-on-failure
bash scripts/test_check_obelisk_server_posture.sh
bash scripts/test_linuxgsm_wrapper_markers.sh
python3 scripts/test_obelisk_cli.py
python3 scripts/test_public_sdk_guardrails.py
```
