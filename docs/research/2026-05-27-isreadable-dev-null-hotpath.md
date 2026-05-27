# Memory::IsReadable `/dev/null` Hot Path Audit

## Objective

Evaluate the cost and risk of `Memory::IsReadable` using `write(/dev/null)` before using it
inside the `ProcessEvent` hot path, and identify a safer minimal benchmark or replacement
direction.

## Environment

- Host: `tyronsur`
- Kernel: `Linux 6.8.0-94-generic #96-Ubuntu SMP PREEMPT_DYNAMIC Fri Jan 9 20:36:55 UTC 2026`
- CPU: AMD Ryzen 7 5800X, 16 logical CPUs
- Obelisk commit: `9fd99e0`
- Scope: local/offline C++ probes only; no ARK server start, attach, markers, commits, or
  runtime edits.

## Hypothesis

`write(/dev/null, ptr, size)` is probably too expensive for repeated `ProcessEvent` work,
but may still be acceptable for startup validation or gated scanners if it reliably
rejects unreadable memory.

## Method

Compiled temporary local probes under `/tmp` with `g++ -O2 -std=c++17`.

The first probe directly called `write` on `/dev/null` with:

- a valid stack buffer,
- pointer `0x1`,
- high unmapped pointer `0x7ffffffff000`,
- a `PROT_NONE` anonymous mapping.

It then timed 1,000,000 successful 64-byte checks. The second probe compared two
alternatives:

- cached `/proc/self/maps` range/perms lookup with binary search,
- `process_vm_readv(getpid(), ...)` into a small local buffer.

## Evidence

Current implementation:

- `ue/Memory.cpp:137` opens `/dev/null` once and returns `write(fd, ptr, size) >= 0`.

Local result for `/dev/null`:

```text
valid_1 ret=1 errno=0 (Success)
valid_64 ret=64 errno=0 (Success)
low_bad_1 ret=1 errno=0 (Success)
low_bad_64 ret=64 errno=0 (Success)
high_bad_64 ret=64 errno=0 (Success)
prot_none_64 ret=64 errno=0 (Success)
write_dev_null valid_64 ns_per_call=198.795
direct_byte_check ns_per_call=0.422356
```

Local result for alternatives:

```text
maps ranges=40
valid process_vm=1 errno=0 (Success) maps_read=1
low_bad process_vm=0 errno=14 (Bad address) maps_read=0
prot_none process_vm=0 errno=14 (Bad address) maps_read=0
maps_cached valid_64 ns_per_call=8.19388
process_vm_readv valid_64 ns_per_call=837.781
```

Hot-path sites:

- `hooks/ProcessEventHook.cpp:389` enters `ProcessEvent_Detour`.
- `hooks/ProcessEventHook.cpp:398` calls `GetFunctionNameIndex` only when pre/post
  callbacks or chat reflection are enabled.
- `hooks/ProcessEventHook.cpp:238` currently gates a `UObjectProbe` read through
  `Memory::IsReadable`.
- `hooks/ProcessEventHook.cpp:217` uses `Memory::IsReadable` in tracing, but tracing is
  skipped when `OBELISK_PE_TRACE_LIMIT=0`.
- `hooks/ProcessEventHook.cpp:105` and `hooks/ProcessEventHook.cpp:142` use
  `Memory::IsReadable` during hook target validation/installation, not per event.

## Result

Recommendation: replace `Memory::IsReadable` before relying on it for `ProcessEvent` hot
path safety. Do not leave it as-is.

The current `/dev/null` implementation is not a real readability probe on this Linux host:
it returned success for low invalid addresses, an unmapped high address, and a `PROT_NONE`
mapping. The cost is also unsuitable as a routine hot-path guard: about 199 ns per call
locally before accounting for contention and cache effects in a real server.

Preferred replacement direction:

1. Use direct reads in the core `ProcessEvent` path only after structural gating makes the
   pointer provenance strong. The `function` argument is supplied by UE4 itself; for stable
   filtered callbacks, reading `NamePrivate.ComparisonIndex` should not need a syscall.
2. For arbitrary scanner/research addresses, replace `write(/dev/null)` with a cached
   `/proc/self/maps` readable-range check. The local microbenchmark measured about 8 ns per
   check and it correctly rejected unmapped and `PROT_NONE` ranges. Treat it as a mapping
   and permission filter, not a race-proof proof that a subsequent dereference cannot fault.
3. Keep `process_vm_readv` as a debug/research fallback when the question is "can the
   kernel copy these bytes right now?" It correctly returned `EFAULT` for bad addresses but
   measured about 838 ns per 64-byte check, worse than the current syscall path.

## Rejected paths

- `write(/dev/null)` as a safety probe: rejected because it does not validate user memory
  on this host.
- `process_vm_readv` in the `ProcessEvent` hot path: rejected for normal use because it is
  a per-call syscall and measured roughly 4.2x slower than the current `/dev/null` probe.
- signal-handler based speculative reads: not benchmarked here; still high-risk in a
  hooked runtime because it changes process-wide signal behavior and complicates crash
  diagnosis.

## Risks

- Cached maps can become stale after `mmap`, `munmap`, `mprotect`, plugin load/unload, or
  JIT-like allocation changes. A runtime implementation should refresh on demand after a
  miss, and should make startup/plugin lifecycle refresh explicit.
- A maps check only proves the requested range lies inside a currently readable mapping; it
  does not prevent a concurrent unmap race. For Obelisk's current use, this is acceptable
  for scanner triage and better than the current false-positive probe.
- Removing the hot-path guard without a replacement should be limited to UE-owned arguments
  with strong provenance. Arbitrary param decoding still needs bounded metadata and range
  checks.

## Next steps

1. Add a small unit or standalone test that asserts the current `/dev/null` probe returns
   true for a `PROT_NONE` mapping on Linux. This preserves the negative evidence before
   replacing the implementation.
2. Implement an internal readable-map cache for scanner/research reads, with an explicit
   refresh API and an overflow-safe `start + size` check.
3. Refactor `ProcessEvent` name-index extraction to avoid syscall-style readability checks
   on every enabled callback/chat-reflection event. Benchmark the detour with callbacks
   disabled, filtered callbacks enabled, and chat reflection enabled.
4. Keep all live validation behind the existing isolated-debug gates; no live/shared
   server should run broad `ProcessEvent` tracing or scanner probes for this change.

## Skill updates needed

None immediately. If runtime code is changed, update the relevant runtime/hooking guidance
to say that `/dev/null` writes are not an accepted readability probe on Linux.
