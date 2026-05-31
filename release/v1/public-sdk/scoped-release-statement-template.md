# Scoped v1 SDK Release Statement Template

Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.

This scoped statement records reviewed post-v1 outcomes for surfaces that are already
marked post-v1 in docs/public_sdk_surfaces.json. It is not a v1.0 stable, complete SDK,
full SDK, or production SDK claim while top-level blockers remain planning.

obelisk.lifecycle_ops_recovery.v1: post-v1 - no plugin watchdog API, plugin crash recovery API, hot plugin reload API, Obelisk hot reload API, process restart orchestration API, server recovery API, operator reload command API, detached-worker ingress API, or restart-state recovery API is included in v1
obelisk.command_chat_response_path.v1: post-v1 - no command/chat response path, public CallProcessEvent path, chat reply API, send-chat API, broadcast/notices API, moderation API, raw UE pointer response API, raw ProcessEvent response API, or raw FString response API is included in v1
obelisk.commands_replies.v1: post-v1 - no public command SDK/router, console command API, RCON command API, admin command API, player command API, chat replies, send-chat, broadcast/notices API, or moderation API is included in v1
obelisk.permissions_admin.v1: post-v1 - no permission groups, admin groups, grant/revoke API, admin actions, permission cache ABI, storage/persistence, operator ingress, command router, command/chat response path, replies/send-chat, moderation authority, or ban/kick API is included in v1
obelisk.inventory_items_mutation.v1: post-v1 - no Inventory SDK, Items SDK, give item API, remove item API, kits/rewards API, engram/progression API, inventory lookup, item handles, item mutation, return override, or ResourceHandle API is included in v1
obelisk.player_services_economy_mobility.v1: post-v1 - no economy API, shop API, rewards API, kits API, stats API, homes API, teleport API, safe-zone API, area policy API, broadcast/timed notice service, or cross-instance persistence API is included in v1
obelisk.operator_ingress_storage.v1: post-v1 - no RCON, operator reload command API, Unicode/operator text encoding API, webhook, database/storage, secret manager, external ingress, or cross-instance storage API is included in v1
obelisk.gameplay_tick_callbacks.v1: post-v1 - no server tick callback API, UE gameplay tick callback API, module tick callback API, per-frame hook API, or gameplay timers API is included in v1
