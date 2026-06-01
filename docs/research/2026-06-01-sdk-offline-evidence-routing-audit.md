# SDK Offline Evidence Routing Audit

Date: 2026-06-01

## Scope

This note audits already-produced offline evidence under
`/servidor/ark/workspace-offline` for the current SDK blocker chain:

- player identity / principal lifecycle;
- command/chat response path planning.

No broad scans, runtime probes, server operations, protected dump reads, commits, pushes,
tags, Discord updates, or fixture regeneration were performed. Commands were read-only
metadata, JSON, docs, and checker reads against existing artifacts.

## Player Identity Evidence Already Present

Current completed offline routes for the reviewed ARK binary hash
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`:

- Base offline identity root:
  `/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/`
- Distinct vanilla-gdb identity root:
  `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/`
- Principal policy root:
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`

The existing reflection inventory manifests report candidate-only
`players-identity-lifecycle-intake` coverage for 12 requested and 12 matched targets.
The first-evidence readiness checker, with the lifecycle and principal policy manifests
supplied, reports:

- fixture coverage: `12/12`;
- reflection inventory accepted: `true`;
- distinct second-source layout accepted with no missing, inconclusive, or rejected rows;
- accepted candidate lifecycle anchors:
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`;
- current primary blocker: `approved_runtime_evidence_missing`;
- `promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`.

The lifecycle-anchor candidate manifest and principal invalidation policy manifest both
pass their schema-specific checkers and `validate_offline_artifact_gate.py --mode consume`.
They remain candidate-only planning evidence. They do not promote public player identity,
permissions, commands, lookup, `ResourceHandle`, mutation, return override, runtime hooks,
or public SDK readiness.

Do not rerun broad FName/GObjects/core discovery, admin focal planning, 12-target
second-source layout, or lifecycle-layout extraction for this binary unless the binary hash
changes or a reviewed artifact contradicts the current evidence. The next useful step is
the separately approved bounded runtime principal lifecycle evidence route described in
`docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md`.

## Command/Chat Response Evidence Already Present

The response-path planning root is:

```text
/servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601/
```

It contains base and vanilla-gdb focal snapshots for:

- `ShooterPlayerController.ClientChatMessage`;
- `ShooterPlayerController.ClientServerChatDirectMessage`;
- `ShooterPlayerController.ClientServerChatMessage`.

The readiness report is
`command-chat-response-route-planning-readiness.json`. It reports
`planning_layout_gate.ready=true`, `ready_scope=planning_only`, and
`promotion_gate.ready=false` with blocker `planning_layout_intake_not_promotion_gate`.
The route manifest records distinct base and candidate core identities. The command/chat
response public readiness checker reports:

- `valid=true`;
- `accepted_for_planning=true`;
- `planning_only=true`;
- `readiness_status=compared`;
- decisions status `blocked`;
- `promotion_ready=false`;
- `public_abi_ready=false`;
- `public_header_allowed=false`;
- `public_sdk_ready=false`;
- `runtime_ready=false`.

Do not repeat the static response thunk orientation or distinct second-source layout route
for this binary unless the binary hash, target set, or snapshot evidence changes. The
remaining work is not another offline layout pass; it is the dependency chain:
player principal runtime evidence, permissions/admin promotion, then a copied response
contract and public ABI review.

## Checker / Documentation Gap

Player identity has enough route-level documentation and machine guards to prevent most
repeat work:

- `scripts/check_player_identity_first_evidence_readiness.py`;
- `scripts/check_player_identity_lifecycle_anchor_candidates.py`;
- `scripts/check_player_identity_principal_invalidation_policy.py`;
- `scripts/check_player_identity_runtime_principal_lifecycle_evidence.py`;
- `scripts/validate_offline_artifact_gate.py` consume-mode support for the candidate
  identity manifests.

Command/chat response has useful guards. The route-level gap identified in this audit has
now been hardened in the offline artifact gate:

- `scripts/check_command_chat_response_static_orientation.py` covers bounded static
  orientation;
- `scripts/check_command_chat_response_public_readiness.py` covers the existing
  second-source readiness report plus blocked public contract decisions;
- `validate_offline_artifact_gate.py` still rejects static orientation reports as artifact
  gate schemas, and now recognizes
  `obelisk.command-chat-response-route-planning-distinct-second-source.v1` in consume mode.

The route-level consume gate verifies the three exact response targets through the existing
readiness report, requires distinct base/candidate artifact identities, checks the
referenced `command-chat-response-route-planning-readiness.json`, requires
`planning_layout_gate.ready=true`, and fails closed on public/runtime/promotion overclaims.
Promote mode remains blocked for this schema, and `promotion_ready=false`,
`public_sdk_ready=false`, and `runtime_ready=false` remain the required posture. This is a
documentation/checker hardening item only; it did not rerun discovery or promote the
response path.

## Read-Only Commands Used

Representative commands from this audit:

```bash
git -C /home/flowcommunity-ark/Obelisk rev-parse --short HEAD
git -C /home/flowcommunity-ark/Obelisk status --short
find /servidor/ark/workspace-offline -maxdepth 4 -type f \( -iname '*identity*' -o -iname '*player*' -o -iname '*command*' -o -iname '*response*' -o -iname '*sdk*' -o -iname '*routing*' \) -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
rg --files docs/research | rg -i 'offline|identity|player|command|response|exec|routing|sdk'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_first_evidence_readiness.py --json ...
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_lifecycle_anchor_candidates.py --json ...
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_principal_invalidation_policy.py --json ...
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py --mode consume --json ...
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_chat_response_public_readiness.py --json
```
