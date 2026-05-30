# Plugin Loader Bootstrap State

## Objective

Record the runtime crash found while validating the experimental `oChatLogger` plugin on
`arkserver2`, and the state-management rule that follows from it.

## Environment

- Instance id: `arkserver2`
- Map: `TheIsland`
- Obelisk commit: `fa3cef7`
- ARK binary: `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- ARK binary hash: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Runtime mode: `OBELISK_WRAPPER_PROFILE=observer-debug`
- Plugin state: `oChatLogger` enabled only for `arkserver2`
- Evidence log: `/servidor/ark/workspace-offline/live-validation-logs/arkserver2-chat-plugin-load-20260529T082647Z.log`

## Hypothesis

The first plugin validation crash was caused by C++ static initialization order in the
`LD_PRELOAD` bootstrap path, not by the chat event ABI itself.

## Evidence

The failing run stopped after:

```text
Loading plugin: oChatLogger.so
```

GDB showed `SIGFPE` in `std::__detail::_Mod_range_hashing::operator()` with denominator
zero while `AddPluginOwnerToken()` accessed the owner-token `unordered_map`. The map had
not been safely constructed for the bootstrap path.

After moving plugin owner, registration, and callback maps/mutexes to first-use
process-lifetime storage and converting `oChatLogger` to a small C plugin, the isolated
run logged:

```text
ProcessEvent absolute x64 hook installed successfully
Scanning for plugins in /servidor/ark/obelisk/plugins. Found 1 candidate(s).
Loading plugin: oChatLogger.so
[Plugin] [oChatLogger] Loaded.
[Plugin] [oChatLogger] Registered ChatMessageEvent callback.
Plugin oChatLogger.so initialized successfully.
```

## Result

Confirmed. Plugin load and callback registration now survive the `LD_PRELOAD` bootstrap
window on `arkserver2`. This proves bootstrap/plugin lifecycle viability for the chat
smoke plugin, but it does not prove actual `ChatMessageEvent` delivery from a real chat
message.

## Risks

- Do not use namespace-scope or destructible function-local STL containers for plugin
  owner-token maps, callback registration maps, or lifecycle mutexes in the preload path.
- Process-lifetime storage is deliberate here: the runtime must prefer valid state through
  shutdown over destructor-order cleanup for small registry objects.
- `oChatLogger` remains experimental and safe-disabled by default. It logs event metadata
  and copied message size only, not raw chat text or player identity.

## Next Steps

Superseded: later `arkserver` copied-log evidence validated plugin-facing delivery for
send modes `0,1,2,3`. Keep this runbook command only as a historical template for future
regression/revalidation windows; it is not standing approval.

- Run one current-turn operator-approved `arkserver` / Ragnarok beta-test mode-coverage
  window after sending the current-turn operator-approved beta notice. The approval must
  name exact marker/env deltas, restart behavior, rollback, evidence capture, and notice
  path. Use the `enable-chat-events` marker,
  `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`,
  `allow-experimental-observers`, `OBELISK_CHAT_EVENTS_BINARY_SHA256` set to the supported
  ARK hash, `OBELISK_CHAT_EVENTS_DISPATCH_LIMIT` positive, `enable-process-event-hook`,
  and `oChatLogger` allowlisted only for `arkserver`. `disable-plugins` must be absent for
  the plugin load window.
- Treat these copied-log lines as the success markers for that future delivery test:

```text
Chat message event producer enabled for ShooterGameServer SHA256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.
[Plugin] [oChatLogger] Registered ChatMessageEvent callback.
[Plugin] [oChatLogger] ChatMessageEvent received sequence=<nonzero> send_mode=<recognized> flags=<copied-payload-bit-set> message_size=<controlled-size>. mode_count=<n> first_observed=<true|false>.
```

  Validate the copied beta-window log offline with:

```bash
scripts/analyze_chat_delivery_log.py \
  --expected-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --require-send-modes 0,1,2,3 \
  --require-workspace \
  --fail-on-quality-blockers \
  --json \
  /servidor/ark/workspace-offline/<copied-beta-window-log>
```

  The analyzer requires the producer gate, `oChatLogger` registration, at least one
  accepted delivery event with a nonzero sequence, copied-payload flag, known send mode,
  controlled message size, and no raw chat text or sender/player identity logging. It
  rejects direct live-server log paths under `/servidor/ark`; copy evidence into
  `/servidor/ark/workspace-offline` first.

  `enable-chat-reflection` logs are historical observer evidence and do not prove
  plugin-facing `ChatMessageEvent` delivery.
- Preserve copied log evidence, then restore stable markers and safe-disabled plugin
  config exactly as named by the current-turn rollback approval.
