# Ragnarok Read-Only Posture Snapshot

## Objective

Record the current live-like Ragnarok posture without changing server state.

## Snapshot

- Timestamp: `20260527T185153Z`
- Snapshot directory:
  `/servidor/ark/obelisk/dumps/supervisor/20260527T185153Z`
- Instance: `arkserver`
- Map: `Ragnarok`
- Process: exactly one `ShooterGameServer` process observed.
- Action type: read-only supervisor snapshot; no restart, marker edit, deploy, attach,
  scanner, `gcore`, or broad trace was performed.

## Result

Stable posture passed for the currently running process:

```text
stable; instance=arkserver; process_event_hook=1; plugins_disabled=1; libobelisk_mapped=1; scanner_debug_native_exec_absent=1
```

Quiet posture failed because experimental chat reflection is still active:

```text
chat_reflection_gate_env=1
chat_reflection_binary_sha256=present
```

This matches the existing protected-live policy: do not change Ragnarok while players are
testing. Removing `enable-chat-reflection` still requires an explicit operator maintenance
window followed by `scripts/check_obelisk_server_posture.sh --expect-stable
--forbid-chat-reflection`.

## Next Step

Keep all development and investigation offline or on an approved debug target. When a
maintenance window exists, remove only the Ragnarok chat reflection gate, restart
`arkserver`, and verify stable quiet posture.
