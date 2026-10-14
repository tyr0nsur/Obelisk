# ObeliskNative suite — staged implementation

Updated 14 October 2026. The commercial implementation stays in the private
repository. The public repository contains presentation and redacted progress.
Functional equivalence is a roadmap with independent acceptance for each module.

| Stage | Delivered foundation | Acceptance still required |
| --- | --- | --- |
| Utility commands | oEssentials: help, rules, MOTD and configured server info; synchronous directed replies, arguments, ASCII casefold and cooperative lifecycle | Real-client UI, Steam and two real players |
| SDK command extension | Appended C ABI slot at offset 264, full table 312 bytes; capability bit 15; exact existing registrations unchanged | Wider source ports and gameplay-specific APIs |
| Permissions | Private offline SQLite roles, exact/subtree rules, deny precedence and membership expiry | Trusted Steam/Epic principal mapping and live consumers |
| Economy | Private offline integral balances, credits, debits and transfers; transactional rollback and idempotent operation IDs | Trusted live identity, administration and verified game delivery |
| Migration | Inspect/dry-run copied Permissions/ArkShop configs and coherent offline SQLite snapshots; redacted reports and explicit blockers | Reviewed import/apply protocol and field/permission mappings |
| Shop and kits | Live /shop and /kits catalogs; private transactional reservations, kit quota/cooldown and exact receipts | Verified full-quantity inventory delivery and trusted live wallet subject |
| Homes/player tools | Live session /sethome /home /homes /delhome; guarded self-only engine teleport binding and native position query | Real-client movement acceptance and durable account/world identity |
| Chat/announcements | Live /chatlist /chatglobal /tell using observed session destinations, mute and rate limits | Two real players; cross-map and scheduled broadcast services |
| Dino/structure/tribe policies | Live /dino mounted IDs, /structure aimed ID and /tribe native group ID query commands | Real-client queries, enumeration and permission-checked mutations |

The first utility package is independent implementation using Obelisk's C ABI.
A DLL does not run on the Linux runtime; source ports require adaptation and
recompilation. Permissions and game-native identifiers keep explicit namespaces;
a numeric native observation is not automatically a Steam/Epic authenticated
account. Store tests never establish live game effects.

## Verification

The current full build passes 158/158 CTest cases, including real dlopen/dlclose
integration of oEssentials. Those fixtures exercise hot discovery after startup,
case/argument routing, separate mock origins, config reload, pause/resume,
stop/start, invalid config rollback, symlink/path traversal and selected metadata
identity rejection before config writes. SQLite tests use real databases and two
concurrent connections, rollback triggers, expiry and reopening persistence.

oEssentials was published after the actual server started with oPing alone.
Eleven successful operator requests exercised new-ID start, status, pause/resume,
reload and stop/start without changing the game PID. Both plugins ended running.
A2S reports TheIsland, 70 slots and protected access. The private deployment
artifact records those transitions separately. Client presentation is pending. The existing native
ping/identity client acceptance and its limits remain in
[OPING_PROTOTYPE.md](OPING_PROTOTYPE.md). Full server stopping still needs a clean
acceptance run after the known abort; this is a prototype milestone.

## Delivery order

1. Finish real Steam/Epic multiplayer command/session acceptance and clean stop.
2. Establish authoritative identity/session destinations and managed game-thread
   scheduling/readiness, then attach permission and wallet services.
3. Deliver one vanilla item transaction with receipts and idempotency before kits,
   sell operations, dinos or rewards. Implement position/teleport for homes only
   after permissions and stale-session rejection work.
4. Add broadcasts and cluster routing, followed by individual structure, dino
   and tribe policies. Measure parity by accepted behaviors, not a raw function
   count or whole-suite percentage.

The [catalog](research/obelisk-suite-catalog.json) captures module dependencies;
the [API contract requirements](research/arkapi_functional_contract.json) capture
source-port needs. Both are original project specifications, not upstream ABI or
implementation copies.


## Four-module deployment

The ABI now preserves all earlier prefixes and appends copied chat-session and
command-world records plus a self-only teleport operation (312-byte full table).
Native bindings were checked against 80 evidence proofs, nine class bindings and
14 registrations; their instruction data split into 132 bounded mapped checks.
Startup validates those mapped checks before exposing native queries. Validation
of bytes and class ownership does not establish gameplay acceptance.

Four new modules started after the actual server was already running. Thirty-two
successful operator requests exercised start/status, pause/resume, reload and
stop/start for each, without changing the game process. Six modules ended
running. TheIsland, 70 slots, protected access and the current profile were
preserved. Full build: 156 CTests; public SDK guards: 214; manager guards: 66;
migration: 46; operator client: 4. The SDK installer now publishes precisely the
four public headers; the fresh install/consumer layout test passes.

Session homes use process-local points keyed to a generated runtime session.
They disappear on reconnect or plugin reload and currently target this fixed
TheIsland laboratory. They do not use an observed platform ID as an authenticated
account or promise safe cross-map travel. Engine movement is enabled explicitly
by the operator; dead, sleeping and riding characters are refused, coordinates
are bounded and the engine collision path preserves current rotation. A positive
engine return is checked with a new scoped position query; client acceptance is
still pending. Private HomesStore persistence is a separate future integration.

The shop delivery boolean can mean partial delivery. It cannot establish the
purchased quantity; no purchase or kit fulfillment is enabled by this milestone.
Attempting/uncertain receipts block duplicate delivery and automatic refund;
only verified no-delivery can refund the private transaction.

## Original gameplay parity increment

The [parity contract](GAMEPLAY_PARITY_CONTRACT.md) and dated ASE ecosystem
inventory fix the comparison by product, version, configuration and scenario.
Each public catalog entry has pending behavior dimensions; listing it does not
establish equivalence. No upstream plugin/framework source is incorporated.

The private command-permission service requires an explicit trusted authority,
exact scope, fresh ACL decisions, principal revisions and expiry checks after a
slow resolver. The item-delivery verifier compares exact variant quantities and
stack increments under complete, exclusively attributable snapshots. Partial
or unknown delivery remains blocked without automatic refund/retry. Real SQLite
and failure fixtures pass; neither service is linked to the live SDK/runtime.

Exact-build identity research verifies provider/auth callback candidates and
demonstrates that numeric transport IDs and provider masks are not sufficient
authentication. Inventory research checks quantity metadata and the stacking
path, without executing grants. The API remains 312 bytes, six live modules and
20 chat verbs. Current checks: 158 CTests and 214 public SDK guardrails. Live
authority, purchases and kit fulfillment remain disabled pending native evidence
and client acceptance; these are foundations, not whole-product parity.
