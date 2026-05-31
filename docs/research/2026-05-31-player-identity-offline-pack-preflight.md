# Player Identity Offline Pack Preflight

This note records the current offline preflight for closing the two remaining
`players-identity-lifecycle-intake` snapshot gaps without touching a live server.

## Result

No usable `obelisk.reflection-inventory-pack.v1` manifest was found under the current
non-protected durable artifact root:

```bash
find /home/flowcommunity-ark/obelisk-artifacts -maxdepth 4 -type f \
  \( -name 'manifest.json' -o -name '*inventory*manifest*.json' -o -name 'artifact-pack.manifest.json' \)
```

The durable root currently contains normalized artifact packs and a ScriptStruct inventory
pack, but no UFunction reflection-inventory pack with `schema=obelisk.reflection-inventory-pack.v1`.
That means the next player-identity snapshot step cannot be planned from
`/home/flowcommunity-ark/obelisk-artifacts` alone.

## Safe Next Step

The next useful action is to produce or approve a reviewed, non-protected
reflection-inventory pack with:

- `schema=obelisk.reflection-inventory-pack.v1`;
- `status=candidate-only`;
- `promotion_status=not_promoted_candidate_only`;
- complete `artifact_identity` for an offline core;
- `summary.fname_root_ready=true`;
- empty `blockers`;
- a redacted `ufunction-inventory.json` containing
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`.

Once that pack exists outside protected live-server paths, the safe planning command is:

```bash
python3 scripts/plan_ufunction_focal_snapshots.py \
  --inventory-pack <reviewed-reflection-inventory-pack>/manifest.json \
  --target ShooterPlayerController.ServerListPlayers \
  --target ShooterPlayerController.ServerKickPlayer \
  --evidence-obelisk-commit <reviewed-obelisk-id> \
  --json-out <ignored-non-protected-output>/players-identity-admin-focal-plan.json
```

The planner emits candidate-only `inspect_core_ufunctions.py --snapshot-json` commands.
It does not reread a core, execute snapshot commands, promote identity, authorize runtime
work, or create a public SDK surface.

## Boundary

The two missing snapshots close only the admin-surface fixture gap. They do not establish
login/logout lifecycle anchors, principal validity, identity privacy, permission
authority, command routing, economy identity, runtime readiness, mutation, return
override, `ResourceHandle`, or player lookup.
