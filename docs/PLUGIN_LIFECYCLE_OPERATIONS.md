# Native plugin operator lifecycle

The operator requested start, pause, resume, stop and reload after the first
real-client command milestone. These operations control a plugin generation;
the native chat and ProcessEvent hooks remain installed for the process lifetime.
This is a private runtime facility, separate from the public plugin C API.

## Local operator control

Enable both `OBELISK_ENABLE_PLUGIN_CONTROL=1` and the instance marker
`enable-plugin-control`. The runtime creates a local UNIX socket at
`$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock`.
Its parent is private (0700), the socket is 0600, and OS peer credentials must
identify the runtime's operating-system user or root. Requests originating in
the runtime process itself are rejected. A player name, native ID, chat command
or plugin callback grants no authority to operate this socket.

The transport worker validates and queues requests. It never invokes plugin
lifecycle or game functions. An outer ProcessEvent on the bound main thread
pumps at most one request, outside plugin callback and lifecycle scopes.

Examples from an operator shell:

```sh
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" status
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" pause oPing
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" resume oPing
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" reload oPing
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" stop oPing
python3 scripts/obelisk_plugin_ctl.py --socket "$OBELISK_ROOT/state/instances/$OBELISK_INSTANCE_ID/control/operator.sock" start oPing
```

`--timeout-ms` bounds the queue window. An expired queued request is cancelled
and cannot mutate the runtime later. Once execution begins, the handler receives
a separate bounded drain deadline. An `in_progress` or interrupted response has
an unknown final outcome: query status before deciding what to do next. The
client does not automatically repeat mutations.

## Admission and unloading

Each load binds an owner token to a distinct generation before Init. Normal
callbacks start only after successful Init. Registrations capture that binding;
an old callback snapshot cannot become valid when a later library reuses its
address.

Pause closes admission and waits for already admitted executions. It preserves
registrations, plugin data and handles. Already admitted commands may finish
their reply; new commands cannot enter that paused generation. Resume restores
delivery. A drain timeout keeps the code mapped and admission closed.

Hot stop and reload require two optional exports, resolved from that same
plugin mapping:

```cpp
uint32_t ObeliskPlugin_LifecycleCapabilities(); // exactly 1u: managed callbacks only
bool ObeliskPlugin_PrepareUnload();             // true only when safe to unload
```

oPing implements this cooperative contract and has no private background
threads. Flag 1 requires all executable deliveries to use managed runtime
callbacks and forbids live private workers, external callbacks or retained
foreign exception objects. PrepareUnload is a final consistency check after
managed cleanup; it is too late to join a worker that still uses callback data.
Plugins with private background work require a separate protocol before cleanup
and cannot opt into these hot-unload operations. The runtime cannot stop
arbitrary plugin threads or verify a dishonest capability declaration.

Retirement closes callback and registration admission, drains admitted work,
removes registrations and drains deferred user-data cleanup before PrepareUnload
and Shutdown. Code remains mapped on failed cleanup, refusal, exception or drain
timeout. No forced dlclose follows an incomplete barrier.

Reload initializes a fresh copied `.so` generation after retiring the previous
one. Publish replacement plugin files by atomic rename; never overwrite a mapped
inode in place. oPing is compiled without GNU-unique symbols so they do not
implicitly prevent unloading. Pause preserves in-memory state; reload runs
Shutdown and Init and requires the plugin's own persistence for state migration.

## Acceptance

Owner-gate and socket transport fixtures pass. These establish generation
isolation, thread routing, cancellation and admission behavior in tests.
The full build passes 152 CTests. Thirteen actual server requests covered
status, pause/resume, two reloads and stop/start of oPing without changing the
server PID; the final plugin generation is running. The private deployment
artifact records those results separately from fixture success.
Steam, two-player response isolation and broader gameplay acceptance remain
separate pending cases.

Shutdown or PrepareUnload exceptions are terminal for that generation. Status
reports retained code and the last failure; another request does not repeat a
potentially destructive lifecycle call. A false PrepareUnload refusal may be
retried after the cooperative plugin resolves its own condition.
