# Chat Command Readiness Audit

## Objective

Audit whether the minimal copied `ChatMessageEvent` v0.1 surface plus the current chat
examples are enough for plugin-local command parsing tests, and identify the narrowest next
hardening step before any beta-player testing.

This is a repo-local readiness note. It does not approve server access, marker changes,
restarts, `ReflectionScanner`, ptrace/gcore, runtime observation, or `/servidor/ark`
access.

## Decision

The current surface is enough for plugin-local command parsing tests.

The accepted scope is intentionally narrow: a plugin may subscribe to copied
`ChatMessageEvent`, validate ABI/size/flags/send-mode, copy callback-scope message bytes
into plugin-owned memory, parse a plugin-owned prefix and command table, and route to local
handlers with `principal=unknown`.

This is not enough for a public command SDK, player-facing authority, or beta-player command
behavior. It does not provide sender/player identity, permissions, replies, chat send,
moderation, blocking, mutation, return override, UE lookup, raw `FString`, `UObject`,
`UFunction`, raw params, FName/GObjects indices, or persistent identity.

The narrowest next hardening step before beta-player testing is docs/tests, not runtime code
and not an approved live test.

## Evidence Checked

- `include/obelisk/ObeliskApi.h` exposes `ObeliskChatMessageEvent` with only
  `abi_version`, `struct_size`, `send_mode`, reserved padding, copied-payload `flags`,
  process-local `sequence`, and copied UTF-8 `message`.
- `scripts/plugin_local_chat_command_parser_contract.py` models only the copied event
  fields needed by a local parser: ABI version, minimum struct size, send mode, copied
  flag, sequence, and message text.
- `scripts/test_chat_command_parser_contract.py` covers copied-text parsing, non-command
  no-match behavior, malformed event rejection, prefix-at-byte-zero matching, command
  name byte limits, ASCII safe command-name characters, no lowercasing, and a result type
  containing only `name`.
- `plugins/oBaseEvents/oBaseEvents.cpp` contains a disabled-by-default helper that validates
  `ChatMessageEvent`, bounds copied command input to 1024 bytes, recognizes only a local
  `help` command, logs sanitized metadata with `principal=unknown`, and does not reply,
  send chat, mutate game state, block chat, resolve identity, or authorize a sender.
- `tests/sdk_consumer/SdkConsumerFixture.cpp` exercises the active `oBaseEvents` chat helper
  path: it registers one chat callback, ignores messages without the configured prefix,
  accepts `/help`, rejects unknown/invalid/oversized/malformed events, avoids logging raw
  chat text or command arguments, and unregisters the callback during shutdown.
- `plugins/oChatLogger` and `plugins/oChatAudit` remain experimental copied-data examples:
  they validate the event shape and log only bounded metadata or digest counters, not raw
  chat text, sender identity, command outcomes, permission decisions, replies, or mutation.
- `docs/PLUGIN_ARCHITECTURE.md`, `docs/oBaseEvents.md`, and
  `docs/research/2026-05-30-chat-command-helper-roadmap.md` already describe this as a
  plugin-local pattern, not a runtime service or ABI expansion.

## Readiness Boundaries

Accepted for repo-local tests:

- Parser contract tests over copied event fixtures.
- SDK-consumer fixture tests for an example plugin that keeps commands local and
  safe-disabled by default.
- Documentation/guardrail tests that preserve the boundary: copied text only,
  `principal=unknown`, global config only, sanitized logging, callback-scope lifetime, and
  no command SDK claims.

Not accepted for beta-player command behavior:

- Any command that needs a real sender, player, admin, tribe, connection, platform ID, map
  authority, or persistent identity.
- Any permission check that claims to authorize a specific player.
- Any reply, chat-send, moderation, block, mutation, return override, UE lookup, raw
  `ProcessEvent` parameter access, or pointer-derived handle.
- Any first-party `oCommand*` plugin, runtime command router, new `ObeliskApi` function,
  capability bit, event struct, command registry, or installed helper target.

## Next Hardening Step

Do docs/tests next.

The narrowest useful hardening before beta-player testing is to keep a guardrail that locks
this decision in place and fails if the readiness note drifts into runtime-code or live-test
approval. The guardrail should require these claims to remain explicit:

- plugin-local command parsing tests are allowed over copied `ChatMessageEvent`;
- the parser result has no identity, permission, reply, mutation, or authority fields;
- `oBaseEvents` is the only current command-like example and remains disabled by default;
- `oChatLogger` and `oChatAudit` stay copied metadata/audit examples, not command examples;
- the next step is docs/tests, not runtime code or an approved live test.

Runtime code should wait until a concrete test gap is identified that cannot be covered by
the existing parser contract or SDK-consumer fixture. An approved live test should wait until
there is an operator-approved beta-player plan for copied notification delivery or a future
identity/permission/response API; this note does not create that approval.
