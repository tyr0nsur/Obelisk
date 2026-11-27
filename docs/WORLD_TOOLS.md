# ObeliskNative World Tools prototype

`oWorldTools` provides four read-only commands using copied native observations
for the player issuing the current command. Its default configuration is
disabled with an empty instance allowlist.

| Command | Current scope |
|---|---|
| `/whereami` | Current player's character XYZ position in engine world units. |
| `/tribe` | Current player's native tribe ID; zero displays no tribe. |
| `/dino` | The current mounted dino's native uint32 ID pair. |
| `/structure` | Native ID of the structure at which the current player aims. |

Command names fold ASCII case. Only trailing spaces/tabs are accepted;
arguments such as another player name are rejected. Each reply uses the current
owner/invocation scope and originating controller. Missing data produces a
clear unavailable response; a zero tribe ID remains a valid no-tribe result.
Position output rejects nonfinite values. Dino/structure scope does not include
map enumeration, counts, inventory, editing, ownership changes, admin decisions
or a persistent lookup handle. Native IDs are observations with map/instance
context and do not establish account authentication or authorization.

Configuration is read once at initialization; a managed reload loads updated
values. Exactly these four keys are accepted:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "prefix": "ObeliskNative"
}
```

The prefix must contain 1–64 valid UTF-8 bytes and no ASCII control characters.
The config is bounded to 8 KB. Activating a named instance requires setting
`enabled` and adding its exact ID to the allowlist. Unknown keys, malformed
types, invalid instance names and invalid prefixes reject initialization.

The plugin checks the copied world query, command matching and reply capabilities
and advertised API tail size before registration. No UE pointer, player name or
native account identifier is retained. It writes no player observations to logs,
creates no worker threads and requests the managed callback-only unload contract.
Pause/resume/stop/reload use the runtime's existing owner generation gate and
drained cleanup before library closure.

The real shared-library integration fixture exercises position/tribe/dino/
structure formatting, two distinct mock origins, missing fields and runtime
context, invalid ABI/nonfinite position, argument boundaries, instance scoping,
pause/resume/reload/stop/start and invalid config recovery. Those mocks test the
plugin's contract; they are separate from actual in-game acceptance.

Live availability requires the current exact-build native adapter and a connected
character. Client visibility, current mount and aimed structure values still
require real game observations after deployment. A successful targeted RPC call
is not a client acknowledgement.
