# Current Linux native bindings for the ObeliskNative suite

Research date: 2026-10-14. This is private source documentation. These addresses,
layouts, declarations and byte proofs must not be copied into the public
presentation repository.

The inspected executable is the installed ASE public dedicated server, version
361.7, Steam build 21241282, 86,269,536 bytes, SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
The Epic 361.8 client is a distinct build. Existing client command evidence does
not establish gameplay acceptance for the additional bindings below.

The tracked [private profile](native_suite_profile_361_7.json) contains 80 exact
byte proofs, nine canonical class bindings and fourteen native registrations.
The [offline verifier](../../scripts/research/native_suite_bindings.py) checked
all of them against this executable. It reads ELF file data and never loads
ARK code, attaches to a process, or modifies the world. Historical reflected
fixtures were not used to establish these layouts.

## Narrow native interfaces

All native object pointers below are private, borrowed and confined to the
current game-thread operation. Return only copied values through the plugin API.
Resolve the current player character afresh, validate its canonical class, and
reject disconnected sessions, missing native objects or invalid finite values.

```cpp
struct NativeVector3 { float X, Y, Z; }; // sizeof == 12, alignof == 4
struct NativeRotation3 { float Pitch, Yaw, Roll; }; // sizeof == 12
using GetPlayerCharacter = void* (*)(void* controller);
using GetActorLocation = NativeVector3 (*)(void* actor);
using GetActorRotation = NativeRotation3 (*)(void* actor);
using GetTribeId = uint32_t (*)(void* player_state);
using GetRidingDino = void* (*)(void* character);
using GetAimedUseActor = void* (*)(void* controller);
using GetDinoIds = void (*)(void* dino, uint32_t* id1, uint32_t* id2);
using GetStructureId = uint32_t (*)(void* structure);
using IsRider = bool (*)(void* character);
using IsDeadOrDying = bool (*)(void* character);
using K2Teleport = bool (*)(void* actor, NativeVector3 location,
                           NativeRotation3 rotation, bool simple);
```

The aggregate register declarations follow the observed x86_64 SysV ABI. The
first two vector/rotation floats use one SSE eightbyte and the third uses a
second SSE eightbyte. Ghidra was run without an injected prototype; its scalar
parameter ordering is incomplete for these aggregate calls. The argument/result
movement in the native exec thunks is the ABI evidence.

| Operation | Named owner and native exec | Actual implementation | Result and restrictions |
|---|---|---|---|
| Current player character | `ShooterPlayerController.GetPlayerCharacter`, `0x1543180` | `0xf440a0` | Borrowed `ShooterCharacter*` or null, resolved from a native weak reference. |
| Player world position | `Actor.K2_GetActorLocation`, `0x2eebe10` | `0x2521760` | Copied float3 world position; game thread only. |
| Player rotation | `Actor.K2_GetActorRotation`, `0x2eebe50` | `0x25217b0` | Copied float3 rotation from the root component quaternion. |
| Native tribe ID | `ShooterPlayerState.GetTribeId`, `0x1536120` | `0xfcf050` | Copied uint32 from player state; zero denotes no tribe. |
| Current ridden dino | `ShooterCharacter.GetRidingDino`, `0x159f570` | `0xd81bb0` | Borrowed weak-resolved dino or null; validate `PrimalDinoCharacter` before reading. |
| Player aimed actor | `PlayerController.BPGetAimedUseActor`, `0x2ef45c0` | `0x27871e0`, current ShooterPC override `0xf460c0` | Borrowed actor or null, produced by the engine's current aiming trace. |
| Dino native ID pair | `PrimalDinoCharacter.GetDinoIDs`, `0x1594750` | `0xb03670` | Copies two uint32 values to caller-owned outputs. |
| Structure native ID | `PrimalStructure.BPGetStructureID`, `0x1566e40` | `0xc25fc0` | Static helper copies uint32; null produces zero. |
| Rider state | `PrimalCharacter.IsRider`, `0x158aa40` | current ShooterCharacter override `0xd87d50` | Copied bool. |
| Dead or dying state | `PrimalCharacter.IsDeadOrDying`, `0x158a3e0` | current ShooterCharacter override `0xa43eb0` | Copied bool from native dead/health queries. |
| Engine teleport | `Actor.K2_TeleportTo`, `0x2eebfc0` | `0x25177f0` | Mutable bool result, separate opt-in integration and client acceptance required. |

IDs identify native observations. They do not prove Steam/Epic account
authentication, persistent membership authorization or a stable cross-server
identity. Dino/structure IDs are meaningful with the current map/instance and
object lifecycle; no global lookup or complete census is established here.

## Evidence chains and ownership

`GetPlayerCharacter` is registered to canonical ShooterPlayerController class
storage `0x58eebf0`. The native exec leaves RDI as the controller and calls
`0xf440a0`, then copies RAX to its result. The getter resolves the weak reference
at controller `+0xa54` through `0x1d56a30`, checks object-table bounds, null/dead
conditions and the character's native death bit. The validator compares the
weak serial to the object-table serial. The reflected return-type construction
at `0x14cdfe3` calls `0x182f5d0`, which jumps to the canonical ShooterCharacter
getter `0x13b17c0`, binding global `0x58f0ab0`. Do not substitute
`Controller.Pawn`: a possessed pawn can be a ridden creature.

`K2_GetActorLocation` is registered to Actor class storage `0x59a7d68`. Its exec
copies X/Y from XMM0 and Z from XMM1 after calling `0x2521760`. The native getter
reads `RootComponent` at actor `+0x248`. A populated root normally supplies world
translation at component `+0xe0`; if root flag `+0x100` bit 0 is set it delegates
to the component virtual update slot `+0x4b0`. A null root uses the actor's
native fallback fields. This is why copying the guessed `RelativeLocation`
field is insufficient and why even a position query belongs on the game thread.

`GetTribeId` is registered to canonical ShooterPlayerState `0x58eeb80`. The
native exec copies EAX. The complete getter at `0xfcf050` is
`mov eax,[rdi+0x9f4]; ret`. Independently, native `IsInTribe` calls `0xfc1b10`,
which returns whether the same field is nonzero. Use the already validated
current PlayerState; do not decode the large `MyTribeData` value or trust a
client-provided tribe ID.

`GetRidingDino` uses a weak reference at ShooterCharacter `+0x14c0`, the same
serial validator and a pending-dead filter. Native `GetDinoIDs` copies fields
`+0x1828` and `+0x182c`. Both native registration and the exec tail jump identify
the method. Validate canonical PrimalDinoCharacter `0x58f08c8` first. This
provides an immediate read-only `/dino` scope through the current mount without
world enumeration or exposing an object pointer.

`BPGetAimedUseActor` invokes controller virtual slot `+0xe58` with four null
optional/default arguments. The ShooterPlayerController class binder
`0x154d280` records constructor thunk `0x162ad80`; that thunk invokes
`0xf37da0`, which installs vtable `0x407bcb0` at `0xf37dbf`. Its slot at
`0x407cb08` points to `0xf460c0`. Focused decompilation of that actual override
shows current pawn/character checks and an engine aiming trace returning a
borrowed actor or null. Validate the returned actor against canonical
PrimalStructure `0x58eff18` before calling `BPGetStructureID`. Other actor types
must yield unavailable structure information. The result is a current aimed
object, not a map census or proof of owner permission.

## Teleport state and collision boundary

The current reflected teleport metadata at `0x2dd8860` names `DestLocation`,
`DestRotation`, `bSimpleTeleport` and a bool `ReturnValue`. The exec loads
location in XMM0/XMM1, rotation in XMM2/XMM3, actor in RDI and the bool in ESI.
Native `0x25177f0` preserves the returned AL from either virtual path; the exec
stores AL to the bool result. With `simple=false`, it invokes actor virtual slot
`+0x6a0` with the last two flags false; with `simple=true`, it uses alternate
slot `+0x6a8`. For normal homes, preserve current rotation and use the ordinary
engine path with `simple=false`. Do not turn failure into an unconditional
position write or repeatedly retry a rejected destination.

ShooterCharacter class construction `0x15a1b40` records thunk `0x161a5d0`, which
invokes `0xd3c400`; that constructor installs vtable `0x401caf0`. Native
`IsRider` exec uses slot `+0x16d0`; current slot `0x401e1c0` points to
`0xd87d50`, which returns `(byte[character+0x1260] & 4) != 0`.
`IsDeadOrDying` uses slot `+0x17d8`; current slot `0x401e2c8` points to
`0xa43eb0`, which checks virtual native dead state and nonpositive health.

Sleeping has no separately registered no-argument getter. Its **read-only** bit
is verified independently from current metadata: PrimalCharacter metadata root
`0x1791680` obtains its canonical class through `0x139df20`; the named
`bIsSleeping` property at `0x17a30ec` consumes generated offset/mask resolver
`0x1650040`. The resolver's setter vtable at `0x41e7c10` points to
`0x17e2c40`, which changes bit 0 at object `+0x894`. Reading one byte and testing
mask 1 reproduces this current native property. **Never call that setter**; it
exists in the research chain to establish the field, not to authorize mutation.

Before a homes teleport, require a current connected session, live validated
character, ordinary non-riding/non-sleeping state, a saved location in the same
instance/map scope, bounded finite coordinates, policy/cooldown approval and an
explicit main-thread mutation route. Compare the copied post-call position with
the requested destination before claiming arrival. Native collision rejection
must preserve the home and avoid consuming a success cooldown. Real client
acceptance must cover collision failure, disconnected stale session, death,
riding, sleeping and normal arrival; static proofs cannot replace those tests.

## Shop and kit grant research

Current `GiveItem` is registered on **ShooterCheatManager**, not on
ShooterPlayerController: exec `0x15c5f50` parses `blueprintPath`,
`quantityOverride`, `qualityOverride` and `bForceBlueprint`, then calls
`0xda42d0`. That helper uses the cheat manager's owner controller and routes to
controller helper `0xf71e50`, which discards the temporary returned-item array.
This is unsuitable as the initial transactional shop contract.

Focused decompilation of underlying controller helper `0xf71810` shows a
caller-owned `TArray<UPrimalItem*>` output, blueprint resolution, native
authority/character/inventory checks and item creation through `0xb790d0`.
For some item types it loops over the requested quantity and returns an OR of
successful item creations: **true can mean a partial delivery**. Charging a full
purchase or decrementing a kit from that bool alone would misreport fulfillment.
The exact receipt still requires bounded copying of native item identities,
quantity/stack effects and inventory ownership, plus a durable operation state
for partial/unknown outcomes. Do not automatically replay an uncertain grant
after a process restart.

`VictoryCore.GiveItemToCharacter`, exec `0x15ebcf0`, calls `0x12ad760` with a
caller-owned aggregate return. It names character, item class, count, quality
and auto-equip inputs. Its aggregate result and cleanup are not a proven receipt
either. `PrimalItem.AddNewItem` and `PrimalInventoryComponent.AddItemObject*`
are additional exact current registration candidates, not enabled suite actions.
No item grant, money change or inventory mutation was performed by this audit.

## Reproduction and recorded scope

```sh
python3 scripts/research/native_suite_bindings.py \
  --binary /servidor/ark/obelisk-lab/server/ShooterGame/Binaries/Linux/ShooterGameServer
```

The verifier result is 80 byte proofs, nine class bindings and fourteen native
registrations, unchanged executable, no native code executed and gameplay
acceptance false. It deliberately fails a different SHA even if some addresses
or signatures still match.

Initial candidates were derived using the existing private lab ELF navigation
tool, `bin/migrate-chat-profile.py`: literal UTF32/ASCII names, exact native
registration argument movement, canonical class storage, executable segment
bounds and unwind-table function starts. Focused Ghidra 12.1 runs used
`-noanalysis`, no prototype injection, a bounded function window, 2 GB heap and
two CPUs; temporary imported projects were removed by the lab runner. The ARK
executable was checked unchanged before and after each run.

Private lab evidence includes `logs/suite-native-anchor-candidates.json`,
`suite-current-function-metadata.json`, `suite-current-read-only-profile.json`,
`suite-current-native-binding-profile.json` and focused `.c`/`.asm.txt`/run JSON
for `get-player-character`, `k2-teleport`, `aimed-actor`, `cheat-giveitem` and
`controller-giveitem`. Those files are research evidence, not live acceptance
logs. Startup byte rechecks, fixtures and real client observations must be
reported as separate stages by the integrating runtime.
