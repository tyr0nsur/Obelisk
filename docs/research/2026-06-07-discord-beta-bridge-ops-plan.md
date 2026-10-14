# Discord Beta Bridge Ops Plan

Date: 2026-06-07

## Scope

This note records the proposed operator workflow for letting the Obelisk lead coordinate
beta testers through Discord without turning Discord messages into runtime evidence,
server authority, SDK progress, or release readiness.

It is an offline plan only. It does not send Discord messages, read Discord, create a
bot, authorize RCON, start/stop/restart ARK servers, touch `/servidor/ark`, capture raw
player text, or grant SDK/P0 progress.

## Current Capability

The repository already has `scripts/send_discord_embed.py`. That helper is outbound-only:
it can send guarded embed notices through configured webhooks such as
`OBELISK_BETA_TEST_WEBHOOK_URL`, after dry-run review and explicit send confirmation.

Webhook delivery is not enough for a clear beta-testing workflow because webhooks cannot
reliably read tester replies, maintain structured state, or provide slash-command style
interaction. For two-way coordination, use a bot/bridge instead of trying to make
webhooks bidirectional.

Implementation checkpoint, 2026-06-07 `20:22 CEST`:

- `scripts/discord_beta_bridge.py` exists as an offline-first bridge scaffold.
- `scripts/check_discord_beta_bridge_plan.py` validates the plan/non-authorization
  boundary.
- `local/discord-bot.env` is ignored by Git. Tooling reports only redacted token state
  such as `token_present`; it must not print, store in docs, or repeat token values.
- The token pasted in chat is compromised and must be rotated before any live bot run.
- Live-run preflight now requires a non-secret
  `OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC` attestation in `YYYY-MM-DDTHH:MM:SSZ`
  format on or after `2026-06-07T00:00:00Z`; a token without that attestation is
  blocked and token/attestation values stay redacted in config output.
- `python3 scripts/discord_beta_bridge.py --check-config --json` is valid only for
  offline posture when no token is present. Once a token is present, config validity also
  requires a current rotation attestation and the `discord.py` dependency.
- Dependency detection uses module/package discovery for `discord.py` during config
  checks; it does not import or connect Discord.
- If the system Python reports `discord_py_missing`, run the offline config check with
  the local ignored venv that has the dependency installed:
  `local/discord-bridge-venv/bin/python scripts/discord_beta_bridge.py --check-config --json --require-token`.
- Local dependency probe showed `local/discord-bridge-venv` has `discord.py 2.7.1`.
  With that interpreter and an otherwise configured token/channel/guild, missing
  `OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC` remains the sole config blocker.
- Current posture remains `token_present=true` but `config_valid=false` until the
  rotation attestation is supplied. Config output must show only redacted token state,
  never the bot token value.
- Validation passed after Worker F hardening:
  `python3 -m unittest scripts.test_discord_beta_bridge
  scripts.test_check_discord_beta_bridge_plan scripts.test_send_discord_embed`
  (`32 OK`).

Security hardening checkpoint, 2026-06-07:

- Event JSONL writes are metadata-only. `write_event` rejects raw user/message/player
  fields, secret/webhook/token-shaped strings, and positive authorization/progress/evidence
  aliases before creating or appending the sink.
- Generated bridge events carry `event_sink_semantics=metadata_only`,
  `redacted_metadata_only=true`, `raw_user_id_retained=false`, and explicit false
  non-authorization flags.
- The plan checker now validates `event_sink_semantics` and `live_run_preflight`
  sections, including `requires_rotated_token_attestation=true`,
  `requires_discord_py_dependency=true`, and false Discord read/send/connect flags for
  plan validation.
- Authorization/progress/evidence aliases fail closed even when they appear outside the
  canonical `non_authorization` block.
- The outbound webhook helper refuses embed text that claims runtime evidence,
  approved in-game evidence, Discord/live-op authorization, SDK/P0 progress, or public /
  stable / Plugin Hub / publication readiness.
- No live Discord send/read/connect, RCON, `/servidor/ark` access, commit, tag, or push
  was performed for this checkpoint.

Local blocker hardening checkpoint, 2026-06-07:

- Config report generation now fails closed if a raw bot token would be included in the
  JSON report.
- Focused tests scrub Discord-related environment variables so local test runs cannot
  inherit an operator token.
- Focused validation passed with the local venv:
  `env -u OBELISK_DISCORD_BOT_TOKEN -u OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC -u OBELISK_DISCORD_GUILD_ID -u OBELISK_DISCORD_BETA_CHANNEL_ID -u OBELISK_DISCORD_BRIDGE_EVENT_SINK -u OBELISK_DISCORD_BRIDGE_SALT local/discord-bridge-venv/bin/python -m unittest scripts.test_discord_beta_bridge scripts.test_check_discord_beta_bridge_plan`
  (`23 OK`).

Channel correction checkpoint, 2026-06-07:

- The configured beta webhook URL was reported to deliver to the old channel
  `1509864304520855646`.
- The approved bidirectional beta tester channel is `1513238083741683934`, matching
  `OBELISK_DISCORD_BETA_CHANNEL_ID` in the ignored bot env file.
- Future operational beta notices for tester coordination should use the bot/channel
  path. `scripts/prepare_player_principal_lifecycle_beta_notice.py` now defaults to
  `scripts/discord_beta_bridge.py --send-beta-notice`, and the legacy beta webhook path
  is deprecated/fail-closed for real sends. A webhook URL cannot be redirected by passing
  a channel id.
- A correction notice was sent successfully through the bot to channel
  `1513238083741683934`. This remains communication metadata only, not runtime evidence,
  SDK/P0 progress, readiness, Plugin Hub readiness, or publication authority.

Event summary checkpoint, 2026-06-08:

- `scripts/discord_beta_bridge.py --summarize-events` summarizes the local redacted
  `local/discord-beta-bridge/events.jsonl` sink without connecting to Discord. It reports
  event counts, latest event per actor alias, latest tester milestone per actor alias,
  recent metadata-only events, invalid-row diagnostics without retaining raw lines, and
  attention hints such as loading, cluster transfer, or redacted issue follow-up.
- The summary schema is `obelisk.discord-beta-bridge-event-summary.v1`. It carries
  explicit false non-authorization flags and cannot authorize Discord sends/reads, RCON,
  server operations, live-log reads, runtime capture, runtime evidence, SDK/P0 progress,
  public/stable readiness, Plugin Hub readiness, or publication.
- Focused validation after the summary path and related bridge controls:
  `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_check_discord_beta_bridge_plan scripts.test_send_discord_embed`
  as part of the lead-run Discord/commands-replies suite (`148 OK` total for that suite).

## Proposed Bridge

Add a dedicated Discord bot for a single beta tester channel, with least-privilege
permissions:

- View Channel
- Send Messages
- Read Message History
- Use Application Commands

Prefer slash commands and button/modal interactions over free-form channel scraping. Avoid
the privileged Message Content intent unless the operator explicitly decides raw message
content is needed. The bridge should collect structured tester state, not raw chat logs.

Suggested channel:

- `#obelisk-beta-testers`

Suggested local secrets file, ignored by Git:

- `local/discord-bot.env`
- `OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC` is required beside any bot token before
  `--run`; it is an operator attestation only, not evidence or authorization.
- Offline live-run preflight/config check, using the local venv when needed:
  `local/discord-bridge-venv/bin/python scripts/discord_beta_bridge.py --check-config --json --require-token`

Suggested local event sink, ignored by Git:

- `local/discord-beta-bridge/events.jsonl`

The bridge may write redacted structured events locally. The lead can read the JSONL file
or run a local monitor while supervising a runtime window.

## Slash Commands

Initial command set:

- `/obelisk status`
  - Replies with current beta-test instruction, active target map if one is configured,
    and the non-claim reminder.
- `/obelisk ready map:<Ragnarok|TheIsland|Genesis2>`
  - Tester says they are ready to join or move.
- `/obelisk joined map:<Ragnarok|TheIsland|Genesis2>`
  - Tester confirms they are in the target map.
- `/obelisk logout-ready`
  - Tester confirms they can disconnect when instructed.
- `/obelisk issue type:<crash|timeout|cluster|other> note:<short redacted note>`
  - Tester reports a problem. The note must be redacted and length-limited.
- `/obelisk done`
  - Tester says the current action is complete.

Optional buttons for high-friction runtime windows:

- `Estoy dentro`
- `Listo para logout`
- `Me crasheo`
- `No puedo entrar`
- `Transferido`

Button labels can be localized for testers, but stored event types should remain stable
ASCII identifiers.

## Privacy Boundary

The bridge must not retain:

- raw in-game chat text
- secrets or webhook URLs
- private player data
- IP addresses
- raw identifiers from Steam/EOS/UniqueNetId
- long free-form Discord discussions

Allowed retained fields:

- Discord user snowflake only if needed for tester coordination, or a generated local
  tester alias when possible
- command name
- selected map
- structured status
- short redacted issue category/note
- timestamp
- correlation/run id when the lead supplies one

## Non-Authorization Boundary

Discord bridge events are communication metadata only. They do not authorize or prove:

- runtime evidence
- approved in-game evidence
- live-log reads
- RCON commands
- ARK starts/stops/restarts
- marker/env changes
- SDK/P0 progress
- public SDK readiness
- stable SDK readiness
- Plugin Hub readiness
- publication, tags, or pushes

Runtime evidence still requires the approved copied player-principal lifecycle sibling
set and checker acceptance. A tester clicking `joined` or `logout-ready` is useful
coordination, not evidence.

## Recommended Implementation Shape

Add a small offline-first bridge layer:

- `scripts/discord_beta_bridge.py`
  - Runs the Discord bot only when `OBELISK_DISCORD_BOT_TOKEN`, the rotation
    attestation, and `discord.py` are all present.
  - Refuses live run preflight when a present bot token lacks the required
    `OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC` rotation attestation.
  - Writes redacted JSONL events under `local/discord-beta-bridge/`.
  - Validates event sink records as metadata-only before write.
  - Refuses to run from protected live-server paths.
  - Does not import or call RCON/server-control helpers.
- `scripts/check_discord_beta_bridge_plan.py`
  - Validates the command schema, event privacy flags, and non-authorization fields
    without connecting to Discord.
  - Rejects positive authorization/progress/evidence aliases anywhere in the plan.
- Tests under `scripts/test_discord_beta_bridge.py` and
  `scripts/test_check_discord_beta_bridge_plan.py`
  - Prove no raw text retention, no webhook/token leakage, no live-op authorization, and
    no SDK/runtime/public/stable readiness claim.

Keep the current webhook helper for public/community announcements only. Use the bot
bridge for beta notices and structured tester responses.

## Operational Flow

1. Lead prepares a runtime window or offline test instruction.
2. Lead sends an outbound beta notice through `discord_beta_bridge.py --send-beta-notice`
   after dry-run review and approval for the exact beta window.
3. Testers respond through slash commands/buttons.
4. The bridge writes redacted structured events locally.
5. Lead reads events and decides whether to send RCON broadcasts, ask testers to move, or
   wait. Those server actions still require the standing/current live-op authority and
   safety limits recorded in handoff.
6. Only copied runtime logs and approved checkers can become evidence.

## Rejected Shortcut

Do not rely on the existing webhook as a read channel. It is intentionally outbound-only.
Trying to parse ordinary Discord channel text would add noise, privacy risk, and ambiguous
authority. Structured bot interactions give a clearer operational record and are easier
to keep non-evidence/non-authorizing.
