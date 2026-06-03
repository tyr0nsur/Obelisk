# Executed Test Artifact Command Binding

Date: 2026-06-03

## Summary

Promoted P0 structured evidence already required `executed_test_report` artifacts to be
repo-relative JSON, current-commit bound, output-hash backed, and bound to the active
public SDK surfaces manifest plus public header. This round adds a command/surface
binding: the artifact command or argv must contain a marker for the promoted surface.

## Facts

- `scripts/check_public_sdk_v1_completion.py` now rejects unrelated executed-test
  commands with `executed_test_report:command_surface_mismatch`.
- Accepted markers are intentionally surface-specific:
  - `obelisk.player_identity.v1`: `player_identity`
  - `obelisk.permissions_admin.v1`: `permissions_admin`
  - `obelisk.command_chat_response_path.v1`: `command_chat_response` or
    `command_response`
  - `obelisk.commands_replies.v1`: `commands_replies`
- Existing CMake-style argv such as `commands_replies_sdk_consumer` remains valid when
  the command is for the matching surface.
- This guardrail prevents an unrelated green suite from satisfying a P0 executed-test
  artifact slot merely because it has valid commit/input/hash metadata.

## Non-Claims

- This does not create promoted P0 SDK evidence.
- This does not authorize runtime/server work.
- This does not change complete SDK accounting; SDK remains `0/12`, P0 `0/4`, and
  `stable_claim_allowed=false`.

## Validation

- `python3 -m unittest scripts.test_check_public_sdk_v1_completion` passed 215 tests.
- `python3 scripts/check_public_sdk_v1_completion.py --json` remains blocked by design.
