# oPing: Linux native command prototype

Current target: public ASE, 2026-10-14. A real Epic Games 361.8 client has
confirmed `/ping` -> `pong`, ordinary chat and a disconnect/relogin on the native
Linux dedicated server 361.7. Steam and two-player acceptance remain pending.
Gameplay acceptance is recorded separately from build, fixtures, static
reversing and startup evidence.

## Current target and artifacts

- Active source: `/servidor/obelisk/Obelisk`, branch `reboot/linux-ping-20261013`.
- Sole build: `/servidor/obelisk/build`; pinned dependency sources are in its
  `_deps/{fmt,spdlog,subhook}-src`, with `dependency-sources-manifest.json`.
- Sole server: `/servidor/ark/obelisk-lab/server`, public Steam build 21241282,
  native dedicated-server version 361.7. The available Epic client reports 361.8.
- Runtime: `/servidor/ark/obelisk-lab/runtime-ping`, instance `obelisk-ping`,
  with `oPing.so` and the new `oEssentials.so` utility package.
- Exact executable SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

SteamCMD validated the public installation. The native binary size and SHA1
match its entry in the new official depot manifest; it is not a residual from
an older copied installation. Startup hashes `/proc/self/exe` independently.
Although this ELF equals the archived project binary, historical reflection
scanners and unverified layouts remain disabled. The private adapter below has
been checked directly against this executable.

Steam/Epic crossplay is enabled with `-crossplay` and `-PublicIPForEpic`.
The plugin runs in the server; neither client needs a Workshop mod. These
settings establish configuration; real Epic delivery is recorded below. Keep the
password in the separate mode-0600 access file, not source documentation.

## Private Linux adapter

Current native registrations, exec thunks, vtable, named owner metadata and
focused Ghidra decompilations establish:

| Private field/function | Public-branch value |
| --- | --- |
| ServerSendChatMessage implementation | `0xf76840` |
| Accepted notification ClientServerChatMessage RPC wrapper | `0x136ed90` |
| Notification FName binding offset/global | `0x98` / `0x58eac00` |
| New private-chat ClientServerChatDirectMessage RPC wrapper | `0x136ec60` |
| Direct FName binding offset/global | `0x98` / `0x58eabf8` |
| ShooterPlayerState UID getter | `0xfcf060` |
| UE free | `0x1af8e30` |
| UObject ProcessEvent | `0x1d34e20` |
| ShooterPlayerController/PlayerState class globals | `0x58eebf0` / `0x58eeb80` |
| Controller.PlayerState | `+0x488` |
| PlayerController.NetConnection | `+0x668` |
| PlayerState.PlayerName / UniqueId | `+0x478` / `+0x4c8` |
| UObject.ClassPrivate / UStruct.SuperStruct | `+0x10` / `+0x30` |

Receive ABI is `void(controller*, const FString*, uint8_t mode)`. Reply ABI is
`void(controller*, const FString*, LinearColor value, bool bold)`, with color
in XMM0/XMM1 under SysV. Linux FString is 16 bytes and uses four-byte UTF-32
TCHAR. The UID getter takes an explicit output pointer and PlayerState pointer;
using a trivial C++ by-value struct return would use the wrong registers. Its
owned output is copied and released with UE free, never libc free. Borrowed
name/chat data is never freed.

The inbound prologue comprises 20 bytes of complete, non-relative instructions.
StartupNativeHook uses a 14-byte indirect jump preserving registers, an RX
trampoline, exact-byte validation and single-thread startup installation.
The adapter lives until process exit; no hot removal is supported. The RPC
wrapper is verified by both its prefix and its FName binding; its client-local
HUD implementation is not called.

The user requested chat presentation after confirming the notification reply.
The Direct wrapper is independently checked against this same executable;
focused decompilation follows its client RPC to the chat box rather than the
notification UI. Sixteen extra mapped instruction proofs are added to the
51-proof identity/lifecycle profile. The new build and live deployment are
recorded separately; the original notification acceptance does not establish
the Direct message's visible location or two-player isolation.

The receive signature is unique in this SHA-pinned ELF. Startup verifies its
mapped address directly; it does not depend on the inherited scanner's final
executable-VMA limitation after another patch splits the mapping.

Text and class pointers are copied through `process_vm_readv`. Class ancestry
is bounded to 32 nodes with cycle/incomplete-chain rejection and no pointer
cache. Named property owners are checked in static metadata: a same-name
property on TViewTarget must not be mistaken for Controller.PlayerState.
Replies run synchronously on the process main thread with the same validated
controller and an unchanged NetConnection pointer. UE pointers stay private.

## Plugin contract

The old 216-byte ObeliskApi prefix is preserved. Three command slots extend it
to 240 bytes: register command, unregister command and reply with an owner
token. The current source appends a copied command-player getter and lifecycle
register/unregister slots, preserving the 264-byte prefix on Linux x86_64.
The suite extension appends opt-in verb/case command matching at offset 264;
the current full table is 272 bytes. Original exact registrations stay exact.
COMMAND_REPLIES is advertised only after the native adapter installs. Plugins
must check each appended slot's size coverage, capability and non-null pointer;
the larger table alone does not establish real-client acceptance of its new
features.

`ObeliskCommandApi.h` documents copied callback input and an opaque invocation
token. The token expires when that callback returns. Reply rejects another
owner, thread, expired token or another nested invocation's token. It is not a
persistent player, platform or session identifier.

`oPing` registers exact text `/ping` and replies `pong`. Registered commands
are consumed; ordinary chat continues to the original game implementation.
Callbacks are drained and removed before plugin dlclose. Hot reload of the
native adapter remains outside this prototype.

The experimental `/whoami` example uses `GetCommandPlayerWithOwnerToken` when
COMMAND_PLAYER_SNAPSHOT is available. Its copied name and opaque native ID
views expire with the command callback. Copy bytes before retention; neither
field grants authentication, permissions, lookup or later reply authority.
The typed lifecycle API supplies callback-scoped copied observations, with
post-login and logout-entry phases documented in `ObeliskPlayerLifecycleApi.h`.
These extensions pass the current build and fixture checks. The real Epic
client has confirmed the name and native ID displayed by `/whoami`, and oPing
has received the new typed login event. Logout/relogin and interrupted-session
behavior on this new path remain pending.

## Player and lifecycle observations

Command logs copy player name, platform ID, class-validation results, connection
availability and thread observation. Platform IDs remain strings; their shape
does not identify a storefront.

The recorded observer event FName globals are HandleNewPlayer `0x58ed3d0`, OnLogout
`0x58ed3e0`, and K2_PostLogin `0x59a7578`. The observer checks full FName at
UFunction `+0x18`, ParmsSize at `+0x98`, copied controller parameters and the
current inbound vslot `+0x1360`. K2_PostLogin has an eight-byte parameter block.
The earlier recorded logs did not validate the function owner class, so those
logs explicitly remain observations. The new typed-event path adds owner-class
validation in source; the real Epic login now passes those checks and reaches
the plugin. The remaining logout/relogin and interrupted-session cases are
still pending.
HandleNewPlayer entry alone does not prove login acceptance;
its login flag and returned result must be assessed with real engine/client
behavior. Returned-stage logs avoid identity calls on objects potentially
changed by the original game call.

## Validation and real-client acceptance

The prototype baseline build and 147 CTest checks passed before the 264-byte
identity/lifecycle extension. That extension passed 149/149 CTest checks; its
logs are `logs/identity-lifecycle-build.log` and
`logs/identity-lifecycle-ctest.log`. The current lifecycle/direct-chat build
passes 152/152 checks, recorded in `logs/plugin-lifecycle-build.log` and
`logs/plugin-lifecycle-ctest.log`. Real-client `/whoami` display and typed
login/logout delivery are also recorded. Baseline coverage includes real dlopen of oPing with
two mock controllers, targeted replies, token expiry, wrong thread/owner,
nested dispatch, owner cleanup, native detours, Unicode/unreadable memory and
bounded class ancestry including address reuse. Fixtures do not prove gameplay.

An isolated public-branch server startup confirms both hooks, the verified
command backend, oPing loading, `/ping` registration, and native version 361.7.
The engine reports successful startup in 66.83 seconds. The Internet instance
uses the same binary and profile with Steam/Epic crossplay enabled.

Still required:

1. Steam client command/reply acceptance.
2. Two real players receive only their own directed replies.
3. Typed logout/relogin and event phases are corroborated with real sessions,
   including failed or interrupted logins.
4. Repeated disconnect/relogin creates the proper new context and expired or
   previous invocation tokens remain unusable. An observed relogin alone does
   not prove every session rejection case.

At 23:05:21 UTC on 2026-10-13, the real Epic 361.8 client sent `/ping` (mode 0).
The runtime dispatched the four-byte directed `pong`, logged validated
Controller/PlayerState classes and `main_thread=true`, and the user confirmed
the visible `Server message: pong`. Native name and UID string were captured;
entry events HandleNewPlayer/K2_PostLogin preceded that command. This establishes
the first real client command/reply on native Linux. It does not establish
two-player targeting or Steam acceptance. Details are
stored privately in `logs/public-client-acceptance.json`.

The user also confirmed ordinary chat and a disconnect/relogin in the real
game. Recorded native identity observations remained consistent across that
relogin. These are accepted observations of the baseline session; they do not
establish authentication, storefront provenance, durable identity guarantees or
gameplay acceptance of the newer `/whoami` and typed lifecycle extension.

At 23:58:23 UTC, the updated runtime validated the HandleNewPlayer and
K2_PostLogin owners, copied available name/native ID, and delivered
`login_observed` to oPing with all seven observation flags. HandleNewPlayer's
login flag and returned result were both true. Subsequent command copies
matched the login identity. The runtime sent replies of four and 54 UTF-8
bytes; the user explicitly confirmed the name and native ID shown by
`/whoami`. Its current presentation is a directed server-message notification.
Private chat presentation is being investigated separately. This remains
observation data, not an authentication or storefront guarantee.

Live HandleNewPlayer ParmsSize is 26 bytes; its wrapper reserves 32 bytes of
padded stack storage. Those are distinct measurements. Real-client acceptance
of the new owner-validated typed lifecycle path and assessment of failed or
interrupted logins remain pending.

Evidence is under `/servidor/ark/obelisk-lab/logs`: `public-installation-verification.json`,
`public-manifest-native-entry.json`, `chat-public-native-profile.json`,
`identity-public-profile-audit.json`, focused `chat-public-*.run.json`,
`public-preflight-console.log`, `public-preflight-a2s-info.json`, and the
runtime instance logs. Current target is in `config/current-target.json`.

## Latest extension startup and shutdown observation

The API-264 runtime and updated oPing were installed after 152/152 CTest checks
and the existing chat-reflection benchmark passed. A loopback-bound server
with normal host networking completed engine startup, loaded `/ping`,
`/whoami` and the lifecycle registration, and returned A2S_INFO with TheIsland,
two slots and password protection. This checks installation and startup, not
real-client delivery of the new features. A bounded public test was subsequently
started at 23:46:27 UTC for the operator's real-client command validation.

Stopping with SIGINT ended in SIGABRT. The system journal records the same
result for the earlier API-240 real-client run, so the new extensions are not
established as its cause. There were no runtime shutdown logs. Graceful shutdown
remains an operational issue to diagnose; it is not accepted by the fixture or
startup results. Evidence is retained in `logs/identity-lifecycle-validation.json`
and the referenced startup and shutdown artifacts outside this repository.

## Storage cleanup

The preaquatica installation, extracted project recovery, duplicate laboratory
build/runtime and npm download cache have been removed. Public was moved to
`server`; there is no alternate `server-public` installation. The original
project ZIP remains the single recovery copy of historical work. Cleanup
reclaimed about 22 GiB and is recorded in `logs/cleanup-result.json`.

At 00:06:13 UTC on 14 October, oPing also received `logout_observed` with
flags 31 and sequence 2 after the real Epic session. The previous typed login
had flags 127 and sequence 1. No subsequent typed relogin is recorded yet.

Safe local plugin lifecycle operations are described in
[PLUGIN_LIFECYCLE_OPERATIONS.md](PLUGIN_LIFECYCLE_OPERATIONS.md). They require
cooperative managed-only plugins and retain code on failed cleanup.

## Installed lifecycle and configuration milestone

The final build passes 152/152 CTest cases; private manager guards pass 66/66,
public SDK guards pass 213/213 and the operator client passes four Python tests.
The chat reflection benchmark gate passes. The runtime still exposes the same
264-byte public table; operator lifecycle control adds no public table slots.

The updated runtime is installed on the sole server. Its Direct reply address is
`0x136ec60`, and all 67 mapped instruction checks passed before activation. The
new local operator transport accepts OS-authorized requests and pumps them on the
outer game thread. Thirteen real-server requests exercised pause/resume, two
reloads, stop/start and status. The server PID stayed unchanged across those
requests and oPing is running on generation 4. The private evidence is
`logs/native-plugin-control-deployment.json`; this runtime test does not replace
real-client chat UI, Steam or two-player acceptance.

The staged legacy Game.ini and access-preserving GameUserSettings.ini are now
installed. TheIsland's current world and character were backed up before the
change. The character profile hash remains identical; A2S confirms TheIsland,
70 slots and password protection. Historical world/player saves were not found.
Gameplay effects of the restored rates and the character's in-game appearance
still require the operator's client check.

Stopping the preceding runtime again ended with SIGABRT (signal 6), as previously
recorded. This shutdown issue remains unresolved; safe hot plugin transitions do
not establish a clean whole-server stop. The launcher now refuses a second live
instance and only removes a dead, owned private control socket before a future
launch. The current Internet test window is bounded to 24 hours.


## Suite foundation deployment — 14 October 2026

The 272-byte runtime passed 153/153 CTests, 213 public-SDK guards, 66 manager
guards and four operator-client tests. The standalone migration inspector passed
46 tests. These counts describe separate suites, not ArkApi coverage.

The core was upgraded with current saves and configuration backed up. The new
server process then started with oPing alone. oEssentials was atomically published
after startup and its previously unknown ID was discovered through local operator
`start`. Eleven requests exercised start/status, pause/status, resume, reload,
status, stop/status and start/status. The game process remained unchanged across
those operations, both plugins finished running and oEssentials completed its
third load. A2S reports TheIsland, 70 slots and protected access.

The four utility commands, argument routing and UTF-8 configuration have real
library fixture coverage; their in-game UI acceptance is pending. Private SQLite
permissions/wallets remain an offline library, not a live permission/economy API.
No source or target bindings are published in the public showcase. See
[SUITE_STATUS.md](SUITE_STATUS.md).
