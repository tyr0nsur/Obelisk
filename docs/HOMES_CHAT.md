# Homes storage and advanced chat

These are original ObeliskNative modules. Source and native implementation
details stay in this private repository. Compilation, fixture execution, live
registration, native RPC dispatch, and actual client acceptance are separate
evidence stages; none implies another automatically.

## Advanced chat plugin

`oAdvancedChat` registers four managed, argument-aware commands:

| Command | Behavior |
| --- | --- |
| `/chathelp` | Shows usage and the current observed session token. |
| `/chatlist [page]` | Lists eight observed destinations per page with copied display names. |
| `/chatglobal <message>` | Formats and sends a message to the complete observed roster. |
| `/tell <session> <message>` | Sends a formatted whisper to one observed destination and echoes it to the sender. |

Command names accept ASCII case variants. Messages retain UTF-8 and are limited
to 512 bytes, excluding prefixes and display names. Control characters and line
breaks are rejected. Configurable global/whisper prefixes are limited to 64 UTF-8
bytes. Display names are presentation only; neither names nor numeric token
shape establishes a platform account, permission, or durable identity.

The native transport requires the same active command callback, owner token,
invocation token, destination session token, and process epoch. The callback
copies a bounded roster of at most 64 sessions; an incomplete roster rejects the
entire global operation before dispatch. This roster contains observed chat
destinations and is not an authoritative list of every online player. A true
native send result means the checked RPC was dispatched; client receipt still
needs gameplay acceptance. A destination that disappears while sending can
cause partial dispatch, which receives an explicit private explanation.

Configuration defaults to disabled with an empty instance allowlist. Its eight
keys are `enabled`, `allow_all_instances`, `instance_allowlist`, `global_prefix`,
`whisper_prefix`, `burst_messages`, `rate_window_ms`, and `muted_sessions`. Each
muted entry contains an explicit `session_token` and `process_epoch`; it affects
only this plugin's messages from that runtime session. It does not mute ordinary
ARK chat or authenticate an administrator. The limiter uses a monotonic clock,
bounded burst/window settings, and rejects time regression. Hot reload starts a
new plugin generation and resets transient limiter/mute state from configuration.

The plugin retains no invocation token, UE pointer, worker task, or native player
object. All registrations belong to the plugin owner and its cooperative
lifecycle. Shutdown removes registrations before executable code is closed.

## Reusable chat routing policy

`AdvancedChatRouter` supplies actual copied destination plans for global, local,
tribe, and whisper channels. Local routing checks finite positions and radius;
tribe routing requires an explicit native group observation; world-scoped
channels compare explicit fingerprints. Missing context rejects a request rather
than broadening its audience. Muting and a sliding rate window apply to the
sender. The current plugin activates global and whisper transport; it does not
advertise local/tribe transport without complete recipient context.

Each presence has a private session ID and generation. Disconnect retains a
bounded tombstone, and old generations cannot reinsert themselves. Plans copy
destinations; callers revalidate both sender and recipient immediately before
each native send. Changes to world, tribe, position, mute state, or generation
can reject an outstanding plan. `MaxSessions` bounds identifiers including
tombstones, so storage cannot grow indefinitely. Plans are policy results, not
authorization tokens or delivery acknowledgements; callers must use the checked
transport once inside its native scope.

## Durable homes policy storage

`HomesStore` creates a separate `homes.sqlite3` per instance under an existing
private root. Root/instance directories require mode 0700, database files mode
0600, trusted directory ownership, and no symlink components or hard-linked
database/sidecar files. Paths must remain stable while the connection is open.
The database has its own application ID and transactional schema version 1;
future versions and unrelated schemas are rejected.

Subjects have explicit namespaces and opaque UTF-8 IDs. A caller must establish
their provenance separately. Homes storage never promotes an observed native
ID to an authenticated Steam/Epic account and never grants native permissions.
The world fingerprint must identify the actual map/save supplied by the caller;
a process epoch or map name alone is not a durable save fingerprint.

Home names use 1–32 lowercase ASCII letters, digits, underscore or hyphen.
Positions use finite engine-unit coordinates bounded to absolute magnitude
100,000,000; yaw is within [-180, 180]. Coordinates do not prove a safe landing
position. A home records its world, revision, update time and optional expiration.
Quota counts all unexpired homes for the subject, across worlds. Updating an
existing active home does not spend another slot. Expiry is inactive at its exact
boundary, and retrieving a home for another world rejects it.

Travel policy uses a durable reservation before any action:

1. `ReserveTravel` atomically checks home/world/expiry/cooldown and reserves one
   copied destination for the subject. Leases are 1–300 seconds; cooldowns are
   0–86,400 seconds. Competing connections cannot reserve another destination.
2. `ResolveTravel` revalidates the pending operation, current world, home revision
   and expiry immediately before acting. Editing or removing a home invalidates
   its outstanding destination. The adapter must independently validate the
   current character, movement state, landing location and other gameplay gates.
3. `FinishTravel` records the actual adapter outcome. Failure releases the lease
   without spending cooldown. Success starts cooldown at completion time.

Operation IDs are store-wide. Exact replay returns the original reservation or
completion; changing subject, home, world, cooldown, lease or completion outcome
conflicts. Retry cannot extend an expired lease or consume an operation ID from a
rolled-back transaction. Integral time arithmetic rejects overflow. SQLite
prepared statements, `BEGIN IMMEDIATE`, bounded busy timeout, FULLMUTEX and a
connection mutex preserve the contract across threads and connections.

No method executes a teleport. Durable player homes require a verified account
binding, save fingerprint, native action and gameplay acceptance. The storage
and routing fixtures are useful implementation evidence while those bindings
remain a separate milestone.

## Validation coverage

The dedicated tests exercise UTF-8, namespace/save isolation, exact expiry and
cooldown boundaries, reopen persistence, operation replay/conflict, lease expiry,
home revision invalidation, transaction rollback, concurrent quota/reservation,
private paths, malformed coordinates and future-schema rejection. Router tests
exercise channel boundaries, unknown context, changed position/tribe, stale
disconnect/reconnect destinations, mute expiry, rate windows and clock rollback.
A real `oAdvancedChat.so` fixture covers formatting, observed roster discovery,
targeted whisper/echo, incomplete-roster rejection, stale targets, partial native
dispatch, bounded rate limiting, scoped mute and registration cleanup. Fixture
results are not real-client acceptance.


## Session homes plugin

The separate SDK-only oHomes package now exposes /sethome name, /home name,
/homes and /delhome name. Points use copied native character positions and a
runtime-generated session token/epoch, not an opaque platform ID. They are
process-local, limited to 3 points by default, and clear on reconnect or reload;
pause/resume preserves them. A maximum of 1024 session histories bounds memory.
When a new session reaches that limit, the plugin tries to reclaim disconnected
histories using a complete SDK roster of at most 64 observed active sessions,
within the same command callback. It validates the ABI, record sizes, process
epoch, unique nonzero tokens and presence of the current origin before deleting
histories absent from that roster. Failed, truncated or invalid snapshots leave
every history unchanged and may keep the new save blocked. Points and cooldowns
for sessions still present are preserved. This cleanup neither authenticates an
account nor promotes the observed roster to a census of all online players.
This prototype supports the fixed TheIsland laboratory, not cross-map homes.

An explicitly enabled current-origin teleport checks scope/session/epoch,
controller/connection/character classes, finite coordinates and sleeping/dead/
riding state. It calls the verified engine collision path, preserving rotation.
A positive return spends cooldown and queries position again before reporting
confirmation; uncertain confirmation does not invite immediate retry. Real-client
position and movement acceptance remains pending. HomesStore is independent
private durable storage for a future established account/world integration.
