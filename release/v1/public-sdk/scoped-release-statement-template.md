# Scoped v1 SDK Release Statement Template

Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.

This scoped statement records reviewed post-v1 outcomes for surfaces that are already
marked post-v1 in docs/public_sdk_surfaces.json. It is not a v1.0 stable, complete SDK,
full SDK, or production SDK claim while top-level blockers remain planning.
Scoped checker `8/8` means wording/bookkeeping only. Package-shape/install checks,
support-tier labels, Plugin Hub planning, and any separately recorded standing live
authority are non-evidence/non-progress context only.
They do not authorize v1 completion.
They do not authorize stable/full/production SDK wording.
They do not authorize public SDK readiness.
They do not authorize package/publication readiness.
They do not authorize Plugin Hub readiness.
They do not authorize support-tier activation.
They do not authorize SDK/P0 progress or runtime evidence.

Remaining full-gate blockers not resolved by this scoped statement:

- obelisk.player_identity.v1, obelisk.permissions_admin.v1,
  obelisk.command_chat_response_path.v1, and obelisk.commands_replies.v1 are the P0
  dependency chain for a complete SDK. Do not classify them as post-v1 in this template;
  a scoped non-complete release may only exclude them with explicit no-SDK wording while
  preserving `scripts/check_public_sdk_v1_completion.py --json` as blocked.
- obelisk.structure_census.v1 is explicitly excluded as non-complete accounting; promote
  a narrow copied structure ABI in a later release before claiming StructureEvents,
  census, identity, lookup, build policy, no-collision policy, or ownership lookup.
- obelisk.mission_transfer_dino_tribe.v1 is explicitly excluded as non-complete
  accounting, including mission, transfer, dino policy/cosmetics/carry rules, tribe
  identity/notices/policy, and buff/status.
- GameplayPolicyEvent, ChatMessageEvent, plugin-local chat routing, and inventory copied
  signals remain promoted-experimental-only copied-data seeds; each still needs a promoted,
  excluded, or post-v1 outcome before any full SDK claim.

obelisk.lifecycle_ops_recovery.v1: post-v1 - no plugin watchdog API, plugin crash recovery API, hot plugin reload API, Obelisk hot reload API, process restart orchestration API, server recovery API, operator reload command API, detached-worker ingress API, or restart-state recovery API is included in v1
obelisk.inventory_items_mutation.v1: post-v1 - no Inventory SDK, Items SDK, give item API, remove item API, kits/rewards API, engram/progression API, inventory lookup, item handles, item mutation, return override, or ResourceHandle API is included in v1
obelisk.structure_census.v1: excluded - no StructureEvents SDK, structure census, structure identity, structure lookup, build placement policy, no-collision policy, or ownership lookup API is included in v1
obelisk.object_identity_resource_handle.v1: post-v1 - no object identity, UObject identity, object lookup, ResourceHandle, post-callback object handle, structure handle, item handle, inventory handle, dino handle, tribe handle, buff/status handle, mission/transfer correlation handle, economy/mobility handle, or area-policy object handle API is included in v1
obelisk.mission_transfer_dino_tribe.v1: excluded - mission excluded, transfer excluded, dino_policy excluded, tribe_policy excluded, and buff_status excluded; no Mission SDK, Transfer SDK, Dino SDK, dino colors/cosmetics/carry rules API, Tribe SDK, tribe MOTD, tribe-facing notices, tribe policy API, Buff/status SDK, teleport/spawn API, ownership lookup, or cross-map correlation API is included in v1
obelisk.player_services_economy_mobility.v1: post-v1 - no economy API, shop API, rewards API, kits API, stats API, homes API, teleport API, safe-zone API, area policy API, broadcast/timed notice service, or cross-instance persistence API is included in v1
obelisk.operator_ingress_storage.v1: post-v1 - no RCON, operator reload command API, Unicode/operator text encoding API, webhook, database/storage, secret manager, external ingress, or cross-instance storage API is included in v1
obelisk.gameplay_tick_callbacks.v1: post-v1 - no server tick callback API, UE gameplay tick callback API, module tick callback API, per-frame hook API, or gameplay timers API is included in v1
