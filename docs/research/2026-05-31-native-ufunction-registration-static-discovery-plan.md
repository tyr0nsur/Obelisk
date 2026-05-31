# Native UFunction Registration Static Discovery Plan

Date: 2026-05-31

Status: research plan only; not an artifact gate, not promotion evidence, not public SDK
readiness.

## Purpose

Current static orientation scripts are useful navigation aids, but several of them consume
reviewed addresses or fixed windows. The next useful static-analysis improvement is a
read-only rediscovery tool that starts from target names and the offline
`ShooterGameServer` binary, then rediscovers native UFunction registration evidence from
the ELF each run.

This would reduce repeated manual orientation work for player identity and command/chat
response targets while preserving the existing rule: static thunk orientation does not
replace core evidence, reflection inventory, sanitized focal snapshots, privacy policy, or
runtime promotion gates.

## Proposed Tool

Candidate script:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_native_ufunction_registration_static_discovery.py \
  --binary <offline-ShooterGameServer> \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --target ShooterPlayerController.ServerListPlayers \
  --target ShooterPlayerController.ServerKickPlayer \
  --output-root /tmp/obelisk-native-ufunction-registration/<run-id>
```

Optional enrichment flags may use `radare2` or Ghidra headless when available, but the
baseline workflow must not require those tools in CI or ordinary docs validation.

## Required Behavior

- Reject direct or symlink-resolved inputs and outputs under protected live-server paths.
- Verify the binary SHA before analysis.
- Accept target names or reviewed target-set names, not input addresses.
- Parse ELF load ranges and locate exact target-name strings in readable sections.
- Find text references to those strings and infer nearby registration windows.
- Infer common registrar shape by clustering across targets instead of hardcoding a
  registrar address.
- Require discovered thunk candidates to land in executable text and name strings to land
  in readable data.
- Emit optional redacted radare2/Ghidra windows with hashes in the manifest when tools are
  available.
- Emit blockers instead of weakening checks when a tool is missing or a target is
  ambiguous.

## Proposed Output

Schema candidate: `obelisk.native-ufunction-registration-static-discovery.v1`.

The manifest should record binary SHA, argv, tool provenance, Obelisk commit, target
names, string hits, xref candidates, discovered registration windows, discovered thunk
candidates, registrar cluster summary, redacted thunk-shape summary, blockers, and
non-claims.

Mandatory non-claims:

- `promotion_ready=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `not_artifact_gate=true`
- no identity, lookup, mutation, return override, raw UE pointer access, or callable
  ProcessEvent contract is promoted by this artifact.

## Tests

Use a synthetic ELF or fixture where VMAs change between runs. The test should prove the
script rediscovers names, xrefs, registration windows, and thunks from structure rather
than copying known offsets from current docs or scripts.

## Current Relationship To Player Identity

This plan can accelerate the future player-identity pass by preserving reproducible
orientation for `ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer`. It does not satisfy the active player-identity
blocker. That lane still requires a non-protected copied core, a complete
`obelisk.core-dump-evidence-pack.v1`, a 12-target
`obelisk.reflection-inventory-pack.v1`, sanitized focal snapshots, and reviewed privacy
and invalidation semantics.
