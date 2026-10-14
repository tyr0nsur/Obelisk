# ASE ArkApi functional parity and Linux migration

Private research, checked 2026-10-14. This is a functional inventory and proposed
work order, not an implemented compatibility layer or a public release claim.
Do not copy this technical inventory into the public ObeliskNative showcase.
No upstream implementation or complete header is reproduced here.

## Baseline and sources

The inspected upstream is **ArkServerApi/AseApi**, default branch `main`, commit
`f13b85979254b6b19c8d9255a0fc11c128978b8b`, dated 2025-04-30. The official ASE
download page currently identifies its resource as **3.56**, with Windows and
Visual C++ requirements. Repository HEAD and a distributed release are different
baselines; pending pull requests are not part of this inventory. This concerns
ASE, not the separate ASA API. [Repository][S1], [official ASE resource][S2].

The local comparison uses the installed-source headers
[ObeliskApi.h](../../include/obelisk/ObeliskApi.h),
[ObeliskCommandApi.h](../../include/obelisk/ObeliskCommandApi.h) and
[ObeliskPlayerLifecycleApi.h](../../include/obelisk/ObeliskPlayerLifecycleApi.h).
The comparison baseline was the Linux x64 ABI-1 table of size 264. The subsequent
Command Ex source extension appends opt-in verb/ASCII-case matching, bringing
the table to 272 without changing that prefix. The full build and 153 CTest
cases pass. New-ID installation and cooperative utility-package transitions
passed on the actual server; new command client UI acceptance remains pending.
A declaration alone does not prove a live backend.
[Prototype acceptance](../OPING_PROTOTYPE.md) and
[operator lifecycle acceptance](../PLUGIN_LIFECYCLE_OPERATIONS.md) record the
actual evidence separately. Steam and two-player acceptance remain pending.

## Migration boundary

**Functional compatibility** means implementing a plugin's externally observable
behavior after adapting and recompiling its source for Linux. **Binary ABI
compatibility** would mean loading its existing Windows DLL unchanged; that is
outside this plan. The Windows-facing upstream uses DLL imports/exports,
Windows types and native function calls, while Obelisk supplies a versioned C
function table to native Linux plugins. Matching C++ names or removing
`windows.h` does not establish compatibility. [Upstream base][S3],
[native calls and fields][S4], [Microsoft x64 ABI][S5].

There are three distinct migration layers:

1. Reuse the plugin's portable policy, parsing, configuration and persistence
   logic when its own license permits that reuse.
2. Replace ArkApi entry points and callbacks with an explicit Obelisk adapter.
   Prefer copied UTF-8 data, owner-scoped registrations and capability checks.
3. Reimplement each needed game operation in the private Linux backend, with
   build-specific calling convention, object lifetime and thread validation.
   Windows-generated UE wrappers and field offsets do not become Linux proofs.

A C++ convenience adapter can later preserve selected familiar call patterns
inside the recompiled plugin. It must expose the actual supported subset and
return unavailable for missing behavior. It must not export ArkApi's C++ ABI,
invent UE classes, or manufacture controller pointers from copied identities.

## Domain matrix

Priorities describe proposed development order: **P0** is the migration
foundation, **P1** enables useful read-only command plugins, **P2** adds operator
and persistent services, and **P3** is game mutation requiring separate native
proofs. They are not completion percentages.

| Domain | Upstream functional surface | Obelisk today | Priority and concrete gap |
| --- | --- | --- | --- |
| Plugin loading and metadata | Windows DLL loading, optional explicit Init/Unload exports, plugin information and dependencies. [S6] | Native `.so` Init/GetInfo/Shutdown, copied init paths, plugin owner token; private cooperative operator controls. | **P0:** rewrite entry points; map metadata/config and dependency requirements. No DLL execution or assumed legacy loader-lock behavior. |
| ABI, types and strings | C++ callbacks and UE containers/types, including `FString`, `FName`, actors and generated field/native-call wrappers. [S3][S4][S7] | Preferred typed APIs use C PODs and UTF-8 views. Raw ProcessEvent pointers survive only as gated debug surfaces. | **P0:** keep UE layouts private; specify encoding, lengths, ownership, allocation and ABI coverage. Recompile native dependencies. |
| Callback lifetime and hot management | Hook/command removal and DLL lifecycle entry points. [S6][S8][S9] | Owner generations, admission closure, deadlines and cleanup before Shutdown/dlclose; flag 1 excludes unmanaged live execution. | **P0:** port all executable deliveries to managed callbacks. Detached plugin work prevents cooperative hot unloading. Persist state explicitly across reload. |
| Logging | Framework/plugin diagnostics and runtime utilities. [S2][S10] | `LogInfo`, `LogWarn`, `LogError`. | **P0:** adapt formatting locally; retain bounded, escaped diagnostics and avoid publishing player data. Structured logging remains plugin-side. |
| Runtime utilities and dependencies | Current-directory and UTF-8 helpers, plugin-loaded query and numeric API-version query. [S10] | Init paths and ABI/capability metadata; no public plugin-loaded/dependency discovery service. | **P0/P2:** replace path/version assumptions with explicit Init and capability contracts; define dependencies before porting plugins that query other plugins. |
| Chat commands | Register/remove chat commands; the inspected dispatcher selects the first space-delimited token case-insensitively and supplies the full message. [S8][S11] | Validated legacy slot remains exact; Command Ex adds optional space/tab verb boundary and ASCII casefold; build/fixtures pass, client acceptance is pending. | **P1:** validate the new subset, argument parsing, aliases, collisions and consumption before claiming source-level parity. Exact-only consumers keep their existing behavior. |
| Reply and outbound chat | Targeted and broadcast server/chat messages and notifications. [S12] | Reply to the current command origin only; private direct native route exists, without a public arbitrary-target API. | **P1:** typed destinations and stale-session rejection before deferred or broadcast sends; separate server message, sender-labelled chat and notification semantics. |
| Chat interception | Message observers receive controller, mode and command/spam context and can request suppression. [S8][S13] | Copied text/mode chat-event seed; no copied sender identity, rewrite or suppression contract. Availability remains backend-dependent. | **P1/P2:** first add observed sender/context where verified; moderation requires explicit cancellation and ordering rules. Do not equate notification with policy control. |
| Timers and tick | Per-frame callbacks, a one-second game-timer callback, delayed/recurring scheduling; recurring execution has an asynchronous option. [S8][S14][S15] | Owner-scoped millisecond one-shot/repeating timers on a worker. No public game-thread tick/scheduling API. | **P1:** main-thread managed scheduling for gameplay. Preserve cancellation/drain, repeat/count semantics, pause behavior and overrun rules. A worker timer cannot substitute for an ArkApi game-timer callback that accesses UE. |
| Command player observation | Controller-derived name and native-ID helpers. [S12] | Copied name/opaque native ID valid only during the current command callback. | **P1:** adapt immediate read-only commands now. Never treat the invocation token as a player handle or classify the ID as Steam/Epic by numeric shape. |
| Player lookup and session lifecycle | Player searches and player/game identifiers, with world/controller access. [S12] | Typed login/logout observations; no public player enumeration, lookup, session handle or authentication result. | **P1/P2:** copied online roster plus invalidatable session destinations, explicit identifier namespaces and reconnect tests. Preserve distinctions between native platform ID, game player-data ID and display name. |
| Server readiness and world state | Loading/Ready status plus world, game mode/state and cheat-manager access. [S12] | No public typed world-readiness or world query API. Init is runtime startup, not a ready map. | **P1:** copied readiness/epoch contract; gate game work until ready and invalidate on world replacement. Avoid exposing raw world pointers as a shortcut. |
| Console and RCON | Register/remove console and RCON commands; network RCON dispatch checks authenticated connection state. [S8][S13] | No matching public plugin surface. Local UNIX operator control is a separate OS-authorized facility. | **P2:** copied request/result contracts, proper transport authentication, roles and bounded execution. A chat identity or plugin owner token cannot grant operator authority. |
| Hooks and event policy | Named native detours/trampolines and hook removal; generated wrappers can read/write UE fields. [S9][S4] | Gated raw ProcessEvent observers and copied scalar policy-event seeds. These are not arbitrary native hooks; seeds provide no mutable return override. | **P2/P3:** one named event/action at a time. Record exact pre/post phase, original-call behavior, ordering and supported native build. Native methods need not pass through ProcessEvent. |
| Permissions and administration | Controllers/game wrappers can be used by plugins; the inspected core interfaces do not define a standalone plugin permission-store service. [S7][S12] | No public permission lookup, authenticated principal or grant/revoke API. `/ping` is open to all. | **P2:** separate permission service and explicit principal provenance. Port a plugin's actual permission dependency rather than replacing it with a name/ID guess. |
| Configuration and plugin storage | Core settings/plugin metadata JSON and bundled JSON tooling; inspected core service headers expose no dedicated plugin database API. [S6][S16] | Versioned Init paths and per-instance config; persistence is plugin-owned, without a public storage service. | **P0/P2:** map schemas and paths first; later define transactions, migrations and process/cluster ownership. Preserve existing data with reviewed import, not identity re-keying from observed IDs. |
| HTTP/integrations | Async GET/POST/DELETE helpers document main-thread completion. [S17] | No public HTTP request/completion or external-I/O work API. | **P2:** bounded external I/O with owned cancellation and completion on a managed thread. Outstanding completions must hold their generation or be cancelled before unload. |
| Inventory, items and economy | Inventory quantity/blueprint helpers and item/drop operations, backed by game wrappers. [S12][S7] | Observational policy scalars/category descriptors; no public item lookup, grant/remove, durable item handle or currency service. | **P3:** authoritative typed item operations, transaction/idempotency rules and anti-duplication acceptance. An observed policy event is not an item mutation API. |
| Actors, dinos, structures, tribes and spatial actions | Generated domain wrappers; utilities include spawning, positioning, tribe and spatial queries. [S7][S12] | No public actor/tribe/dino handles, spatial queries, spawn/teleport or structure mutation. | **P3:** develop the minimum copied query/action required by a selected plugin, with ownership, lifetime and failure semantics verified in game. |

## Requirements for the first source ports

The next contract should be driven by small plugins with measurable behavior:

1. **Command information/help plugin:** exact or explicitly supported argument
   parsing, copied invocation identity, targeted UTF-8 reply and per-instance
   config. Acceptance includes ordinary chat, unknown commands and malformed
   arguments; no permission or economy dependency is needed.
2. **Scheduled announcement plugin:** a managed game-thread scheduler plus a
   copied destination/broadcast operation. Define whether missed announcements
   are skipped, replayed once or replayed in full after pause. Test the chosen
   rule; do not send game RPCs from today's timer worker.
3. **Read-only session/audit plugin:** documented login/logout observation phases,
   copied online roster and session invalidation. Test Steam, Epic, two players,
   interrupted login and reconnect independently. Observation is not an
   authenticated principal.
4. **Permission-gated admin plugin:** add the principal/role contract before
   privileged commands or RCON. An operator's OS socket access is a separate
   authority from any in-game role.
5. **Persistent economy/inventory plugin:** only after authoritative identifiers,
   storage migration and game actions exist. Transactions need replay protection
   across disconnect, reload and process restart.

For each port, record its upstream commit/license, native library dependencies,
all ArkApi calls, all direct UE-field accesses and every untracked thread or
callback. Mark each dependency as available, adapted, deferred or unavailable.
Reject initialization when a required capability, covered table slot or backend
is missing; do not silently turn a required operation into success.

The adapter must copy Init strings it retains; read table slots only after
`struct_size` covers them; require matching capability and non-null pointers;
and retain registration ownership until cleanup. Reply views and copied player
views expire with their documented scope. Persistent data must never contain
registration handles, invocation tokens or owner-generation tokens.

## License and provenance facts

The inspected AseApi root license is **MIT**, with notices for ArkServerApi,
Game Servers Hub and Michidu. It permits commercial use/distribution subject to
its notice conditions and warranty disclaimer. This is a fact about that
repository's license, not a grant to redistribute arbitrary third-party plugin
source, purchased DLLs, game assets or separately licensed dependencies.
[Pinned license][S18].

The bundled JSON header identifies nlohmann/json 3.10.2 under MIT and contains
separate third-party notices. Reusing dependencies requires their own notice
inventory; the project license cannot replace it. [Bundled JSON notices][S16].
The official download page separately says its resource must not be reuploaded;
this plan references the resource and does not rehost its binary package. [S2]

This document and its companion functional-contract JSON contain original
requirements, symbol references and source links only. No upstream header,
Windows binary, live player identifier, credential or private server address
has been added. The implementation and this research remain private; the
public ObeliskNative repository continues to contain presentation and metrics.

[S1]: https://github.com/ArkServerApi/AseApi/tree/f13b85979254b6b19c8d9255a0fc11c128978b8b
[S2]: https://www.ark-server-api.com/resources/ase-server-api.32/
[S3]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/API/Base.h
[S4]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/API/Fields.h
[S5]: https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170
[S6]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Private/PluginManager/PluginManager.cpp
[S7]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/API/ARK/Ark.h
[S8]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/ICommands.h
[S9]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/IHooks.h
[S10]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/Tools.h
[S11]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Private/Commands.h
[S12]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/Ark/ArkApiUtils.h
[S13]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Private/Ark/HooksImpl.cpp
[S14]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/Timer.h
[S15]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Private/Tools/Timer.cpp
[S16]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/json.hpp
[S17]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/version/Core/Public/Requests.h
[S18]: https://github.com/ArkServerApi/AseApi/blob/f13b85979254b6b19c8d9255a0fc11c128978b8b/LICENSE
