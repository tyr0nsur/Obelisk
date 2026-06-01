# AseApi/NextGen Name Demand Map

Date: 2026-06-01
Status: dictionary/demand synthesis only; no promotion evidence

## Scope

This note maps high-demand ArkApi-style plugin capability families to candidate
Obelisk SDK surfaces and likely UE4 names worth investigating after the current
identity/principal, permissions/admin, and command/response blocker chain.

Inputs used as demand dictionaries only:

- existing Obelisk research notes, `docs/SDK_V1_COMPATIBILITY.md`,
  `docs/public_sdk_surfaces.json`, and `docs/public_gameplay_events.json`;
- local AseApi reference checkout at `/tmp/aseapi-inspect` because `/tmp/AseApi`
  was not present in this environment;
- local NextGenPlugins clone at `/home/flowcommunity-ark/NextGenPlugins`.

No runtime probing, server access, scanner run, debugger, offset derivation, ABI
change, source porting, command parser inspection, schema extraction, or
implementation copying was performed.

## Hard Boundary

AseApi and NextGenPlugins names below are dictionary/demand signals only. They
must not be used as architecture, behavior, ergonomics, implementation, source,
offset, vtable, layout, ABI, wrapper, constant, schema, command parser, return
semantic, or algorithm sources.

Every UE4 name must be rederived through Obelisk's Linux reflection path:
exact `Class.Function` or `Class.Property` resolution, sanitized snapshots,
distinct second-source comparison, copied/redacted payload design, runtime
observation only in an approved window when required, owner-scoped lifecycle
cleanup, append-only C ABI, and SDK consumer tests.

Public Obelisk APIs must not expose raw UE pointers, `UObject`, `UFunction`,
raw `ProcessEvent` params, raw `FString`, FName/GObjects indices,
`ResourceHandle`, object lookup, mutation, or return override unless a separate
promotion gate explicitly creates that surface.

## Demand Map

| Demand family | Candidate Obelisk surface | Dictionary names to investigate | Current route |
| --- | --- | --- | --- |
| Inventory/item copied signals | `obelisk.inventory_item_copied_signals.v1`, current `GameplayPolicyEvent` backing | `PrimalItem.AllowRemoteAddToInventory`, `PrimalItem.CanUse` / `BPCanUse`, `PrimalItem.AllowEquipItem`, `PrimalItem.CanRepair`, `PrimalItem.UseItemOntoItem`; fields such as `ReturnValue`, `bRequestedByPlayer`, `bIgnoreCooldown` | Preserve copied scalar observations only. Do not widen into public Inventory/Items SDK, item identity, `FItemNetID`, grants, removal, rollback, mutation, or return override. |
| Inventory/item mutation, kits, give-item, shops | `obelisk.inventory_items_mutation.v1`, plus `obelisk.player_services_economy_mobility.v1` and `obelisk.operator_ingress_storage.v1` | `ShooterPlayerController.GiveItem`, `ShooterCheatManager.GiveItem`, `PrimalItem.CraftBlueprint`, controller inventory-use requests such as `ShooterPlayerController.ServerRequestInventoryUseItem*`; item/engram dictionary names such as `UPrimalEngramEntry.*`, `AShooterGameMode.OverrideEngramEntries`, `AShooterGameMode.EngramEntryAutoUnlocks` | High demand from shop/kits/rewards/engrams, but mutation and progression remain blocked behind identity, permissions, storage, item ownership, rollback, abuse controls, and explicit mutation policy. |
| Structure policy, limits, ownership, no-collision | `obelisk.structure_census.v1`, current structure-backed `GameplayPolicyEvent`, later build-policy lane | Already-backed names: `PrimalStructure.AllowStructureAccess`, `PrimalStructure.IsAllowedToDemolish`, `PrimalStructure.SetVariant`, `PrimalStructureItemContainer.VerifyPinCode`, `PrimalStructureItemContainer.AllowToggleActivation`, `PrimalStructureSeating.CanSeat`. Demand-only build names: `PrimalStructure.IsAllowedToBuild`, `PrimalStructure.BPIsAllowedToBuild`, `PrimalStructure.BPIsAllowedToBuildEx`, `PrimalStructure.BPOverrideAllowStructureAccess` | Keep current public surface to copied `field_mask`, `bool_values`, and `int32_values`. Build placement is planning-only until redacted placement snapshots, second-source evidence, location/player redaction, and no-return-override policy are accepted. |
| Homes, teleport, safe zones, mobility, area rules | `obelisk.player_services_economy_mobility.v1`, `obelisk.operator_ingress_storage.v1`, structure/build policy side lanes | Dictionary pressure from `ArkHomes` and `SafeZone`; possible later name seeds include `UWorld.FindTeleportSpot`, spawn/respawn and player-location related GameMode/Controller names, and structure/damage/PvP policy fields such as `AShooterGameMode.bAllowCaveBuildingPvP`, `StructureDamageMultiplier`, `PvPZoneStructureDamageMultiplier` | Do not start from direct teleport/move calls. First useful SDK work is a copied principal plus privacy-scoped location/area-policy model, persistence/cooldowns, permissions, audit, and fail-closed enforcement boundaries. |
| Operator ingress, RCON, reload, Unicode text, storage | `obelisk.operator_ingress_storage.v1`, `obelisk.lifecycle_ops_recovery.v1`, later command/response surfaces | NextGen demand from `ExtendedRcon`, `UnicodeRcon`, reload commands, adverts/MOTD. UE response-name seeds: `ShooterPlayerController.ClientChatMessage`, `ShooterPlayerController.ClientServerChatMessage`, `ShooterPlayerController.ClientServerChatDirectMessage`, `GameMode.Broadcast` | Separate from player identity. Needs ingress trust model, secrets policy, UTF-8 rules, audit, queue lifecycle, storage migration, owner cleanup, and copied response ABI before any public RCON/storage/reply/broadcast API. |
| Lifecycle recovery, plugin crash/reload, scheduled work | Promoted foundation: `obelisk.lifecycle_config_logging.v1`, `obelisk.process_local_timers.v1`; blocker: `obelisk.lifecycle_ops_recovery.v1`; separate blocker: `obelisk.gameplay_tick_callbacks.v1` | NextGen demand from plugin crash manager, reload commands, timer callbacks. AseApi timer/tick vocabulary is demand only, not an Obelisk tick design. | Process-local timers are already foundation. Watchdog, hot reload, restart orchestration, operator reload, crash recovery, and UE gameplay tick callbacks remain separate blocked surfaces. |
| Dino policy, carry, colors, rewards | `obelisk.mission_transfer_dino_tribe.v1` leaf `dino_policy` | `PrimalDinoCharacter.AddPassenger`, `PrimalDinoCharacter.AllowCarryCharacter`, `PrimalDinoCharacter.BPAllowCarryCharacter`, `PrimalDinoCharacter.BPNotifyAddPassenger`, `PrimalDinoCharacter.ServerRequestAttack`, `PrimalDinoCharacter.SetCharacterStatusTameable`, `ShooterPlayerController.ServerRequestDinoCharStats`, `ClientReceiveDinoCharStats`; fields such as `PassengerSeatIndex`, `bForcePassenger`, `bAllowFlyersAndWaterDinos`, `AttackIndex`, `ReturnValue` | Existing compact evidence is internal layout/scalar planning only. Public Dino SDK needs dino/player identity, ownership, privacy, runtime observation, dispatcher lifecycle, ABI tests, and no mutation/return override unless separately promoted. |
| Tribe permissions, MOTD, tribe logs | `obelisk.mission_transfer_dino_tribe.v1` leaf `tribe_policy`, plus future permissions/admin integration | `ShooterPlayerController.AllowTribeGroupPermission`, `ShooterPlayerController.IsInTribe`, `ShooterPlayerController.ServerRequestTribeLog`, `ShooterPlayerController.ClientReceiveTribeLog`, player-state counterparts, tribe-data dictionary names such as `FTribeData.*` | Identity-sensitive. Keep scalar permission/log-request planning separate from blocked string/array payloads. No tribe identity, membership contract, log payload, or permission enforcement API is promoted. |
| Buff/status effects and upload/use restrictions | `obelisk.mission_transfer_dino_tribe.v1` leaf `buff_status` | `PrimalBuff.AllowPostProcessEffect`, `PrimalBuff.BPBuffPreventUploading`, `PrimalBuff.BP_OnBuffLifetimeUpdated`, `PrimalBuff.BuffOverrideInventoryAccessInput`, `PrimalBuff.BPCustomAllowAddBuff`, `PrimalBuff.BPPreventAddingOtherBuff` | Useful for internal copied/redacted status-policy design after compact evidence is refreshed. No public Buff SDK, class/object exposure, runtime hook, mutation, return override, or gameplay semantics are promoted. |
| Missions and transfers | `obelisk.mission_transfer_dino_tribe.v1` leaves `mission` and `transfer` | Mission names: `MissionType.AddPlayerToMission`, `MissionType.BPAllowPlayerToLeaveMission`, `MissionType.BPOnPlayerRemovedFromMission`, `MissionType.GetPlayerUsableItems`. Transfer seed: `ServerTransferredPlayerConfirmationResult.bAccept`; broader transfer/download/upload names stay sensitive. | Mission copied-bool and transfer `bAccept` are internal consume-only slices. Arrays, item payloads, downloaded character/dino data, cross-map state, player identity, mutation, return override, and public SDKs remain blocked. |
| Admin/moderation and player progression | `obelisk.permissions_admin.v1`, `obelisk.player_identity.v1`, later dedicated admin/moderation and progression leaves | `ShooterPlayerController.ServerListPlayers`, `ShooterPlayerController.ServerKickPlayer`, `AShooterGameMode.GetPlayerData*`, `AShooterGameMode.PlayerDatas`, `AShooterGameMode.IDtoPlayerDatas`, engram/level dictionary names | These are evidence/demand seeds only. Admin actions, player lookup, player data, bans/kicks, engram unlocks, and progression mutation require promoted principal identity, fail-closed authorization, privacy/invalidation policy, storage/audit, and mutation policy. |

## Priority After Core Chain

Once identity/principal, permissions/admin query semantics, and command response
are no longer blocked, the highest SDK-completion accelerators from this demand
map are:

1. `operator_ingress_storage`: RCON/reload/storage/webhook demand blocks many
   admin, shop, economy, and automation use cases but is independent of UE
   reflection.
2. `inventory_items_mutation`: shop/kits/rewards and admin tooling all converge
   here, but it must start with copied ownership and rollback policy, not
   direct `GiveItem`.
3. `structure_census` plus build-policy planning: structure limits, safe zones,
   no-collision, and ownership cleanup are common demand, but build placement
   must remain redacted and no-return-override until explicitly promoted.
4. `player_services_economy_mobility`: economy, homes, teleport, and safe zones
   are product-facing families, but they are composite surfaces over identity,
   permissions, storage, location privacy, and mutation/enforcement.
5. `mission_transfer_dino_tribe` leaf accounting: keep each leaf narrow and
   independently promotable. Dino/tribe/buff/mission/transfer demand should not
   be collapsed into one broad public module.
6. `lifecycle_ops_recovery` and `gameplay_tick_callbacks`: plugin crash/reload
   and tick/timer vocabulary remains high-demand, but process-local timers do
   not satisfy watchdog/reload/gameplay tick expectations.

## Exclusions

This note is not Plugin Hub work and does not define Plugin Hub packages,
examples, intake rules, compatibility promises, or a porting path.

This note does not promote public identity, permissions, command routing,
replies, send-chat, broadcasts, RCON, storage, item grants, economy, homes,
teleport, safe zones, structure build policy, dino/tribe/buff/mission/transfer
SDKs, player data, admin actions, progression/engrams, object lookup,
`ResourceHandle`, mutation, return override, runtime readiness, or v1
completion.

Do not cite AseApi or NextGenPlugins line numbers, signatures, structs, command
names, schemas, constants, parser behavior, return values, or hook wrappers as
Obelisk evidence. Use the names above only to choose closed Obelisk target sets
for future reflection snapshots and copied C ABI design reviews.

## Validation

This was a read-only documentation pass. Commands used were limited to `sed`,
`find`, `rg`, `ls`, `test`, and `git status` for local inventory and context.
No build was run because the only edits are research documentation and a README
index entry.
