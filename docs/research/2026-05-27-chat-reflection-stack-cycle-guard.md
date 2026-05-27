# Chat Reflection Stack Cycle Guard

## Objective

Reduce allocation pressure in the internal chat reflection hot path without changing the
public SDK or weakening UFunction/property validation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Target: offline synthetic benchmark and unit tests
- Runtime files:
  - `ue/RuntimeReflection.cpp`
  - `hooks/ProcessEventChatReflection.cpp`
  - `tests/perf/ChatReflectionBenchmark.cpp`
- No ARK server state was changed.

## Hypothesis

`RuntimeReflection::TryReadUFunction()` can keep property-chain cycle detection on stack
because `ReadOptions::MaxProperties` already bounds the number of properties. Removing the
temporary visited `std::vector` should reduce one allocation from every matched reflected
chat path.

The UTF-32 decoder can also reserve its UTF-8 output after validating the `FString`
header, reducing reallocations for non-SSO chat text without changing decode semantics.

## Method

- Replaced the temporary visited vector with a fixed stack array of 64 property pointers.
- Kept the existing `MaxProperties` and `NumParms` checks.
- Added a fail-closed guard if `NumParms` exceeds the stack cycle guard capacity.
- Reserved UTF-8 output capacity once the reflected `FString` char count is validated.
- Added an explicit `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0` short-circuit so observation
  logging disabled at the gate does not run reflection work.
- Rebuilt and ran focused reflection tests.
- Rebuilt `chat_reflection_benchmark` and checked benchmark gates.

## Evidence

Validation commands:

```bash
cmake --build build -j2
ctest --test-dir build --output-on-failure -R 'RuntimeReflectionTests|ChatReflectionTests|ProcessEventChatReflectionTests'
cmake --build build --target chat_reflection_benchmark -j2
./build/chat_reflection_benchmark 20000 | tee /tmp/obelisk-chat-reflection-benchmark-stack-visited.txt
python3 scripts/check_chat_reflection_benchmark.py /tmp/obelisk-chat-reflection-benchmark-stack-visited.txt
```

Observed synthetic benchmark allocation deltas:

```text
hook_like_disabled allocations_per_iter=0
hook_like_enabled_non_chat allocations_per_iter=0
hook_like_chat_limit_zero allocations_per_iter=0
server_send_chat_match allocations_per_iter=2
server_send_chat_decode_utf32 allocations_per_iter=1
hook_like_server_send_chat allocations_per_iter=2
hook_like_server_send_chat_text allocations_per_iter=4
```

The matched metadata path previously allowed 3 allocations per iteration; the text path
previously allowed 7. The standalone UTF-32 decode path now allows 1 allocation for a
non-SSO fixture. The benchmark gate now enforces the lower ceilings and includes the
standalone match/decode cases, not only hook-like cases.

## Result

Confirmed. Stack cycle detection removes one temporary allocation from matched chat
reflection paths, and decode reservation removes repeated string growth allocations while
keeping disabled, non-chat, and log-limit-zero paths allocation-free in the synthetic
hook-like benchmark.

## Risks

- This is still synthetic evidence. It does not include live server tick/hitch behavior.
- Matched chat reflection still allocates for reflected parameter storage and field
  storage.
- Text logging still allocates for UTF-8 decode and sanitized log text, and remains behind
  `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`.

## Next Steps

1. Consider a fixed-capacity internal view for chat fields only if the remaining two
   matched-path allocations become promotion blockers.
2. Keep public SDK chat dispatch blocked until TheIsland A/B runtime validation completes.
3. Do not enable text logging outside a short approved debug window.
