# ObeliskNative Hub local API

The recovered FlowArk dashboard is the application base for ObeliskNative. Its
existing `FLOWARK_*` environment variables and deployment filenames remain
compatibility settings; the product shown to operators is ObeliskNative.

## Catalog and evidence

`GET /api/hub/catalog` returns six original Linux prototype modules and their
commands, requirements and limitations. Their version is an ecosystem preview
version, not a statement that every module has passed client acceptance.

`GET /api/hub/references?search=&family=&page=1&pageSize=20` searches the frozen
2026-10-14 public ASE reference inventory. It contains 157 resource cards,
including the framework and possible duplicate products. Every returned card is
`reference_pending`, `available: false`. Reference records are not installable
ObeliskNative products and do not establish gameplay parity. Page size is 1–50;
search is at most 128 characters. Duplicate and unknown query parameters reject.

All Hub reads require an authenticated `operator` or `owner`. Read permissions
are intentionally separate from permission to mutate plugins.

## Registering local instances

Set `OBELISK_HUB_INSTANCES_FILE` to an absolute operator-managed JSON file with
mode `0600` in a private directory with mode `0700`. The file is configuration,
not an upload or a browser-editable setting. The owning UID must be root or the
dashboard UID. Ancestor symlinks, untrusted writable directories and hardlinked
registry files reject. A root-owned sticky temporary ancestor is permitted for
isolated tests; the immediate private directory must still be `0700`.

```json
{
  "schema_version": 1,
  "instances": [
    {
      "id": "theisland",
      "name": "The Island",
      "socket_path": "/srv/obelisknative/runtime/state/instances/theisland/control/operator.sock",
      "plugin_ids": ["oPing", "oEssentials", "oShopKits", "oHomes", "oAdvancedChat", "oWorldTools"]
    }
  ]
}
```

The ID is the dashboard's configured map ID when correlating server capabilities.
Socket paths must be distinct absolute AF_UNIX socket paths, at most 107 bytes,
without symlink ancestors. The socket must be `0600` in a `0700` directory and
owned by the dashboard UID or root. These checks do not grant Unix permissions:
the dashboard must already have permission to connect. No `sudo`, SSH or remote
shell is invoked.

`GET /api/hub/instances` omits all host paths. `available` reports a valid private
socket node, not a completed control exchange or a healthy game process. Use
`GET /api/hub/instances/:id/plugins` to query actual plugin control state.

## Plugin control

`POST /api/hub/instances/:id/plugins/:pluginId/:action` accepts an empty JSON
object. The supported actions are `start`, `pause`, `resume`, `stop`, and `reload`.
The plugin must be in that instance's explicit allowlist and the own catalog.
The caller must be at least an operator and hold `obelisk.plugins.manage`.
Owners receive that permission by default; explicit per-user deny still applies.
Viewer grants do not bypass the minimum operator role. Existing authentication,
CSRF validation, JSON content type, IP policy and API rate limiting still apply.

The service executes the fixed repository operator client with `/usr/bin/python3`
and fixed argv, a 6-second subprocess deadline and a 64 KiB output cap. The
browser cannot choose a script, command, socket, working directory or host path.
Operations are serialized per registered instance and are never retried.

Responses:

| HTTP | Outcome | Meaning |
| --- | --- | --- |
| 200 | `confirmed`, `ok: true` | Runtime returned a successful operator response. |
| 409 | `confirmed`, `ok: false` | Runtime returned an explicit rejection. |
| 202 | `pending` | In progress, transport disconnected, process deadline, invalid response, or audit commit failed after dispatch. |
| 409 | `previous_outcome_pending` | Query status before issuing another mutation. |

A successful confirmed status query clears the process-local pending barrier.
This is not a persistent job queue or an automatic rollback system. A dashboard
restart discards its local operation history. The runtime's resident safety
checks remain authoritative, and failed cooperative unloads may retain mappings.

Audit availability is checked before dispatch. An audit failure after dispatch
returns a pending outcome and instructs the operator to query status before
continuing. Raw runtime failures, stdout/stderr and host paths are not returned
to the browser.

## Artifacts

Set `OBELISK_HUB_ARTIFACTS_DIR` to an operator-approved release directory containing
`index.json` with `schema_version: 1` and an `artifacts` array. Metadata names are
basenames only. The index and referenced payloads must be regular files, have
trusted ownership, reject hardlinks/symlinks and not be group/world writable.

`GET /api/hub/artifacts` returns validated metadata and explicitly reports
`signature_verified: false`. Index contents do not establish signature validity,
production readiness, accepted gameplay or installation safety.

`GET /api/hub/artifacts/:id/download?file=archive|manifest|signature` streams one
indexed regular file through an already checked descriptor. Archives are capped
at 512 MiB, manifest/signature at 2 MiB. Archive size must match the index. The
client must independently verify the signature and archive hash against a trusted
key using the release verifier before installation. No upload, installer, URL
fetch, arbitrary download path or automatic runtime replacement is exposed.

## Server capabilities

`GET /api/servers/:mapId/capabilities` requires an operator or owner and reports
the actions allowed for that caller. RCON is configured only when the managed
GameUserSettings file explicitly enables it, an admin password exists, and the
map has a valid RCON port. Passwords and paths are omitted. `reachable: null`
means it has not been probed; a configured port does not prove connectivity.

Native plugin control is a separate transport. It does not make RCON moderation
or arbitrary console commands available. Settings saves require a later map
restart. In-game admin allowlist management remains Steam ID based and does not
constitute a verified grant to an Epic native opaque ID.

## Verification

`node --test test/hub.test.js` in `server/` exercises real application
authentication/CSRF, the actual Python control client and an isolated AF_UNIX
protocol fixture. It covers bounded references, role overrides, dispatch once,
pending barriers, audit failures, private paths, indexed downloads and RCON
capability reporting. These are dashboard/control-plane tests, not real-client
ARK gameplay acceptance.

Player observations: `GET /api/players/online` retains `players` for compatibility
and adds `per_map`, `complete`, `source: rcon_listplayers`, `observed_at` and an
explicit unverified observation authority. `complete` only means every requested
map returned recognized RCON output. It is not an authoritative Steam/Epic census.
Disabled or unavailable RCON returns incomplete observation metadata; empty or
malformed replies cannot establish zero online players. Queries use at most four
parallel map requests and preserve stable cluster-order deduplication.

Development JWT fallback is ephemeral and does not read or create a credential
in the checkout. Set `JWT_SECRET_KEY` through the private service environment for
persistent sessions. Production already requires that explicit environment key.
