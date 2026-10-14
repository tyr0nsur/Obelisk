# ObeliskNative suite — staged implementation

Updated 14 October 2026. The commercial implementation stays in the private
repository. The public repository contains presentation and redacted progress.
Functional equivalence is a roadmap with independent acceptance for each module.

| Stage | Delivered foundation | Acceptance still required |
| --- | --- | --- |
| Utility commands | oEssentials: help, rules, MOTD and configured server info; synchronous directed replies, arguments, ASCII casefold and cooperative lifecycle | Real-client UI, Steam and two real players |
| SDK command extension | Appended C ABI slot at offset 264, full table 272 bytes; capability bit 15; exact existing registrations unchanged | Wider source ports and gameplay-specific APIs |
| Permissions | Private offline SQLite roles, exact/subtree rules, deny precedence and membership expiry | Trusted Steam/Epic principal mapping and live consumers |
| Economy | Private offline integral balances, credits, debits and transfers; transactional rollback and idempotent operation IDs | Trusted live identity, administration and verified game delivery |
| Migration | Inspect/dry-run copied Permissions/ArkShop configs and coherent offline SQLite snapshots; redacted reports and explicit blockers | Reviewed import/apply protocol and field/permission mappings |
| Shop and kits | Requirements and acceptance criteria | Typed inventory grant/remove with anti-duplication receipts |
| Homes/player tools | Requirements and acceptance criteria | Authoritative sessions, positions and permission-checked game-thread actions |
| Chat/announcements | Requirements and acceptance criteria | Managed game-thread scheduler, broadcast and world readiness |
| Dino/structure/tribe policies | Requirements and acceptance criteria | Copied domain identities, reconciliation and verified decision hooks |

The first utility package is independent implementation using Obelisk's C ABI.
A DLL does not run on the Linux runtime; source ports require adaptation and
recompilation. Permissions and game-native identifiers keep explicit namespaces;
a numeric native observation is not automatically a Steam/Epic authenticated
account. Store tests never establish live game effects.

## Verification

The current full build passes 153/153 CTest cases, including real dlopen/dlclose
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
