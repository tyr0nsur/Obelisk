# Runtime Lifecycle Guardrail Audit

## Result

Offline static audit at Obelisk `1b545f0` found the current
`PluginManager`/`EventManager`/C ABI guardrails sufficient for continuing toward the
full SDK only under the existing owner-token, copied-event, and debug-gated raw
`ProcessEvent` model.

Verified current coverage:

- `PluginManager` captures per-owner API capabilities, rejects owner-token registration
  while a plugin owner is unloading, and still allows owner-token unregister during
  shutdown cleanup.
- Init failure and unload mark the owner unloading before optional
  `ObeliskPlugin_Shutdown()`, run plugin-owned callback cleanup before `dlclose`, and
  retain the library mapped when cleanup fails.
- Owner cleanup includes raw `EventManager` callbacks, public gameplay/chat registration
  maps, direct copied-event dispatchers, and timers.
- Public SDK growth is statically blocked for player identity/principal, permissions,
  command response, inventory observers, and mutation lanes until promotion work adds
  ABI, owner cleanup, and SDK consumer tests.
- Raw `EventManager` dispatch snapshots callback ids/generations, skips removed
  callbacks, catches plugin/internal exceptions, and only honors pre-callback blocking
  when the registration and live env+marker gate allow it.

## Guardrail Change

Added `scripts/test_event_manager_guardrails.py` because this HEAD had no
`scripts/test_event_manager_guardrails.py` despite raw `EventManager` lifecycle being
part of the plugin unload safety chain. The new static test fixes the existing contract:
process-lifetime singleton state, non-zero/non-live-reused registration ids, owner cleanup
under the dispatch lock, snapshot/id/generation checks, fail-open pre-dispatch exception
handling, post-dispatch exception containment, and dual-gated ProcessEvent blocking.

## Risks / Non-Claims

This audit did not run live servers, markers, restarts, broad tracing, native exec probes,
or runtime observation. It does not promote raw `ProcessEvent` callbacks into a stable SDK
surface, does not authorize public `CallProcessEvent`, and does not add identity, lookup,
mutation, command response, or return-override APIs.

Residual risk before a full SDK promotion is mostly integration breadth: future copied
event families must keep adding explicit `PluginManager::UnregisterPluginCallbacks`
coverage and SDK consumer tests, and docs/examples must continue to teach copied
owner-token APIs instead of borrowed raw UE pointers.

## Validation

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_plugin_manager_guardrails.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_event_manager_guardrails.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_public_sdk_guardrails.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_process_event_hook_guardrails.py
```
