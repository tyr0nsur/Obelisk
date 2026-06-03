# v1 SDK Round: Identity, Static Tooling, and Demand Audit

Date: 2026-05-31
Obelisk checkpoint: `63034fc`
ARK binary hash in current offline evidence lane:
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`

## Summary

Historical status: the two admin sanitized snapshots called out below were later added
and the 12-target `players-identity-lifecycle-intake` planning set is now fixture-backed.
The active P0 blocker is approved runtime principal lifecycle evidence, then reviewed
player identity public contract; this note remains a record of the earlier static-demand
round and should not be used to request more admin snapshots.

This round keeps the v1 route centered on a complete public SDK contract, not on
runtime stability alone. The current v1 completion gate remains blocked by design:
`player_identity`, `structure_census`, and `mission_transfer_dino_tribe` are still
planning surfaces, several broad plugin-demand categories are post-v1 unless explicitly
promoted or excluded, and copied `GameplayPolicyEvent` plus `ChatMessageEvent` seeds do
not satisfy a complete SDK claim.

No agent touched `/servidor/ark`, Discord, GitHub publication, or live servers.

## Findings

- `ChatMessageEvent` is public-safe only for its narrow RC contract: copied UTF-8
  notification, owner-token registration, capability gating, and no sender identity.
  It is not a command SDK, reply/send-chat API, moderation surface, permission surface,
  or v1 completion proof.
- Ghidra headless and radare2 are available locally and can accelerate bounded static
  orientation. They do not replace a complete non-protected core evidence pack,
  reviewed reflection inventory pack, focal snapshots, second-source evidence, or ABI
  promotion gates.
- Static admin thunk orientation currently remains orientation-only for:
  - `ShooterPlayerController.ServerKickPlayer`
  - `ShooterPlayerController.ServerListPlayers`
- The earlier missing `players-identity-lifecycle-intake` admin snapshots are now closed
  in committed fixtures; they remain planning-only and do not satisfy runtime evidence.
- `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` are outside the
  12-target fixture-backed pressure/risk set and are now separate candidate-only planning
  lifecycle anchors; they still do not satisfy approved runtime principal lifecycle
  evidence.

## Shortest Offline Identity Path

Required inputs:

- Offline `ShooterGameServer` with the current hash above.
- Copied ELF core for that binary outside `/servidor/ark`, with no symlink path crossing
  into protected server paths.
- Complete `obelisk.core-dump-evidence-pack.v1` with `evidence_status.status=complete`
  and no failed GDB core inspection.
- Reviewed `obelisk.reflection-inventory-pack.v1` for
  `players-identity-lifecycle-intake`.

Next commands should produce only candidate/internal evidence:

1. Build the complete core evidence pack with reviewed FName/GObjects inputs.
2. Build a full reflection inventory pack for `players-identity-lifecycle-intake`.
3. Build consume-mode first-evidence artifacts only. `promotion_ready`,
   `public_sdk_ready`, and `runtime_ready` must stay false.

Fail closed if any input resolves under `/servidor/ark`, hashes mismatch, evidence packs
are partial, the inventory is direct-core/two-function-only, second-source comparison is
self-comparison or inconclusive, or any player identifier/raw UE/FName/GObjects/pointer
field is copied into public or logged output.

## Demand Dictionary

ArkApi/AseApi/NextGenPlugins demand is useful only as names and module-demand signals. Do
not use it as architecture or ergonomics guidance, and do not copy code, offsets, layouts,
constants, command parsers, return semantics, MSVC/Windows ABI choices, or control flow.

High-demand names seen in local plugin dictionaries, grouped only as planning inputs:

- Identity/permissions/commands: `HandleNewPlayer`, `Logout`,
  `StartNewShooterPlayer`, `AuthPostSpawnInit`, `ServerListPlayers`,
  `ServerKickPlayer`, `ServerSendChatMessage`, `ClientNotifyAdmin`.
- Structures/area policy: `IsAllowedToBuild`, `TakeDamage`, `Die`,
  `AllowStructureAccess`, `IsAllowedToDemolish`, `VerifyPinCode`,
  `ReceiveActorBeginOverlap`, `ReceiveActorEndOverlap`.
- Inventory/items/economy: `AllowRemoteAddToInventory`, `CanUse`, `AllowEquipItem`,
  `CanRepair`, `UseItemOntoItem`, `CraftBlueprint`,
  `ServerRequestInventoryUseItem`, `ServerUnlockEngram`.
- Dino/combat: `CanCarryCharacter`, `AllowCarryCharacter`, `IsAllowedToTransfer`,
  `ForceUpdateColorSets_Implementation`, `CanDragCharacter`, `CanBeCarried`,
  `TakeDamage`, `OnImpact`.
- Tribe/social: `IsTribeWar`, `ServerRequestTribeLog`,
  `ClientReceiveMyTribeOnlineList`, `IsInTribe`, `AllowTribeGroupPermission`.
- Transfer/mission/buff: `ServerTransferredPlayerConfirmationResult`,
  `ServerDownloadTransferredPlayer`, `ServerUploadCurrentCharacterAndItems`,
  `ServerUploadDino`, `AllowDownloadDino`, `BPCustomAllowAddBuff`,
  `BPPreventAddingOtherBuff`, `BPBuffPreventUploading`.

These names are not evidence of SDK readiness or runtime safety.
