#pragma once

#include "core/InventoryPolicyEventDispatcher.h"
#include "ue/InventoryReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventInventoryReflection
{
    enum class GateStatus
    {
        Disabled,
        MissingObserverDebugProfile,
        MissingObserverDebugWindow,
        MissingInstanceMarker,
        MissingBinarySha256,
        UnsupportedBinarySha256,
        Enabled,
    };

    struct Gate
    {
        GateStatus Status = GateStatus::Disabled;
        std::string BinarySha256;

        bool Enabled() const { return Status == GateStatus::Enabled; }
    };

    enum class AttemptStatus
    {
        Disabled,
        NonInventoryFunction,
        Rejected,
        Matched,
    };

    struct Attempt
    {
        AttemptStatus Status = AttemptStatus::Disabled;
        Obelisk::UE::RuntimeReflection::ReadResult Result = {
            Obelisk::UE::RuntimeReflection::ReadStatus::Disabled,
            {},
        };
        Obelisk::UE::InventoryReflection::InventoryInvocation Invocation;
    };

    struct CopiedInventoryPolicyEvent
    {
        Obelisk::Core::InventoryPolicyEventView View;
        std::array<Obelisk::Core::InventoryPolicyScalarValue, 3> ScalarStorage{};
        size_t ScalarCount = 0;
    };

    Gate EvaluateGate(const char* enableInventoryReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedInventoryNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldAttemptRuntimeObservation(uint64_t logLimit, uint64_t dispatchLimit);
    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& logCounter,
                                         uint64_t logLimit,
                                         const std::atomic<uint64_t>& dispatchCounter,
                                         uint64_t dispatchLimit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t logLimit, uint64_t dispatchLimit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);
    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber);
    bool TryReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                   std::atomic<uint64_t>& counter,
                                                   uint64_t limit,
                                                   uint64_t& observationNumber);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
    bool TryBuildCopiedInventoryPolicyEvent(
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation,
        CopiedInventoryPolicyEvent& out);
    size_t MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation);
}
