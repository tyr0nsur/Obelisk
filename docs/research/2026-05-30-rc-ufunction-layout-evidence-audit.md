# RC UFunction Layout Evidence Audit

## Result

The `v0.1.0-rc.1` UFunction evidence claim is target-set-scoped layout evidence only.

Accepted RC backing target sets:

- `minimal-second-source-intake`
- `structure-observer-intake`
- `chat-message-intake`

These support copied `GameplayPolicyEvent` and minimal copied `ChatMessageEvent` backing
layouts. They do not promote a public Inventory SDK, public StructureEvents SDK, broad
chat SDK, command routing, object identity, player identity, `ResourceHandle`,
GObjects/FName lookup, mutation, return override, raw params, UE pointers, or runtime
authority.

## Fixture Boundary

`tests/fixtures/ufunction_snapshots/manifest.json` is intentionally mixed. It includes RC
backing snapshots, internal research snapshots, and post-RC candidates. The whole manifest
must not be cited as RC readiness evidence.

RC readiness must be proven by:

1. the named RC target sets above,
2. an assembled second-source candidate root,
3. `scripts/check_rc_layout_evidence_smoke.sh --candidate-root <root>`,
4. `scripts/check_release_readiness.sh --require-second-source-readiness` on a clean tree.

Snapshot identity fields such as object indices, FName indices, class object indices, and
target values are comparison/correlation fields. They are not stable public identity,
lookup, handle, lifecycle, or complete FName/UFunction discovery evidence.
