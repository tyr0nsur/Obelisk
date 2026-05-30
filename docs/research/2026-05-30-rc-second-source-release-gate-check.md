# RC Second-Source Release Gate Check

## Summary

On 2026-05-30, the local `v0.1.0-rc.1` release gate passed from a tracked-clean
worktree using the assembled RC UFunction second-source root.

This check proves the current core-first RC gate for the documented public scope:
`GameplayPolicyEvent`, resource/event descriptors, and minimal `ChatMessageEvent`.
It does not promote Inventory or Items SDKs, `ResourceHandle`, object identity, lookup,
mutation, return override, GObjects promotion, or additional gameplay module APIs.

## Inputs

Assembled root:

- `/tmp/obelisk-rc-ufunction-second-source-root`
- Manifest SHA256:
  `011a8dfaf79fce2252a1040fca0a9b7dbd6b179d6c4692d4e29e75bcb9ac047a`

Source roots:

- Minimal:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/ufunction-snapshots`
- Structure:
  `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/ufunction-snapshots`
- Chat:
  `/servidor/ark/workspace-offline/chat-message-intake-20260529T000000Z/ufunction-snapshots`

## Commands

```bash
python3 scripts/assemble_rc_ufunction_second_source_root.py \
  --minimal-root /servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/ufunction-snapshots \
  --structure-root /servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/ufunction-snapshots \
  --chat-root /servidor/ark/workspace-offline/chat-message-intake-20260529T000000Z/ufunction-snapshots \
  --output-root /tmp/obelisk-rc-ufunction-second-source-root \
  --replace

scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root /tmp/obelisk-rc-ufunction-second-source-root

rm -rf /tmp/obelisk-rc-second-source
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root /tmp/obelisk-rc-ufunction-second-source-root \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set structure-observer-intake \
  --ufunction-second-source-target-set chat-message-intake \
  --second-source-report-dir /tmp/obelisk-rc-second-source
```

## Result

The smoke check reported:

```text
readiness targets=9 comparable=9 blocked=0 second_source_status=compared gate_mode=second_source_promotion
promotion_gate ready=true blockers=none
ufunction:sdk_chat targets=1 comparable=1 blocked=0 second_source=accepted:1,rejected:0,inconclusive:0,missing:0
ufunction:sdk_inventory targets=2 comparable=2 blocked=0 second_source=accepted:2,rejected:0,inconclusive:0,missing:0
ufunction:sdk_structures targets=6 comparable=6 blocked=0 second_source=accepted:6,rejected:0,inconclusive:0,missing:0
```

`scripts/check_release_readiness.sh --require-second-source-readiness` completed:

```text
Core-first release readiness and gameplay/module second-source promotion checks completed.
```

Release gate coverage included CMake configure/build, 47 CTest tests, script tests,
second-source readiness reports, install layout validation, installed SDK consumer builds,
read-only CLI status, installer dry-runs, `git diff --check`, and final tracked-clean
status. Ignored local directories remained ignored and were not staged: `build/`, `local/`,
and `scripts/__pycache__/`.

## Reports

- `/tmp/obelisk-rc-second-source/ufunction-minimal-second-source-intake-second-source-readiness.json`
  - SHA256: `a51d48f537c19808b0612965236ca39cdfc69105dc8b6d524ac52cdc389e8255`
  - Targets: `4`
  - Comparable: `4`
  - Accepted: `4`
  - Blocked: `0`
- `/tmp/obelisk-rc-second-source/ufunction-structure-observer-intake-second-source-readiness.json`
  - SHA256: `08723429ed8506a1db587c548a11316e0e84c078a79858f6f22d5b5b63c829eb`
  - Targets: `6`
  - Comparable: `6`
  - Accepted: `6`
  - Blocked: `0`
- `/tmp/obelisk-rc-second-source/ufunction-chat-message-intake-second-source-readiness.json`
  - SHA256: `194548a9f88f01da9c806d748f9a72e499a710054f73836e3fb0fc6469548f89`
  - Targets: `1`
  - Comparable: `1`
  - Accepted: `1`
  - Blocked: `0`

## Remaining Release Actions

- Do not tag or push until the operator approves publication.
- If publication is approved, rerun the release gate immediately before tagging so the
  evidence matches the published commit.
- Keep post-RC discovery separate from this scope: Mission copied-bool observer, Item
  return-only policy, and Transfer `bAccept` remain candidate/internal work.
