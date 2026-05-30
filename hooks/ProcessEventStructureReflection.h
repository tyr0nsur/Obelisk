#pragma once

#include "core/StructureEventDispatcher.h"
#include "ue/RuntimeReflection.h"
#include "ue/StructureReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>

namespace Obelisk::Hooks::ProcessEventStructureReflection
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
        NonStructureFunction,
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
        Obelisk::UE::StructureReflection::StructureInvocation Invocation;
    };

    struct CopiedStructureEvent
    {
        Obelisk::Core::StructureEventView View;
        std::array<Obelisk::Core::StructureScalarValue, 6> ScalarStorage{};
        size_t ScalarCount = 0;

        CopiedStructureEvent() = default;

        CopiedStructureEvent(const CopiedStructureEvent& other)
            : View(other.View),
              ScalarStorage(other.ScalarStorage),
              ScalarCount(other.ScalarCount)
        {
            RebindScalarSpan();
        }

        CopiedStructureEvent& operator=(const CopiedStructureEvent& other)
        {
            if (this != &other)
            {
                View = other.View;
                ScalarStorage = other.ScalarStorage;
                ScalarCount = other.ScalarCount;
                RebindScalarSpan();
            }
            return *this;
        }

        CopiedStructureEvent(CopiedStructureEvent&& other) noexcept
            : View(other.View),
              ScalarStorage(other.ScalarStorage),
              ScalarCount(other.ScalarCount)
        {
            RebindScalarSpan();
        }

        CopiedStructureEvent& operator=(CopiedStructureEvent&& other) noexcept
        {
            if (this != &other)
            {
                View = other.View;
                ScalarStorage = other.ScalarStorage;
                ScalarCount = other.ScalarCount;
                RebindScalarSpan();
            }
            return *this;
        }

        void RebindScalarSpan()
        {
            View.Scalars = std::span<const Obelisk::Core::StructureScalarValue>(
                ScalarStorage.data(), ScalarCount);
        }
    };

    Gate EvaluateGate(const char* enableStructureReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedStructureNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldAttemptRuntimeObservation(uint64_t logLimit, uint64_t dispatchLimit);
    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& logCounter,
                                         uint64_t logLimit,
                                         const std::atomic<uint64_t>& dispatchCounter,
                                         uint64_t dispatchLimit);
    bool ShouldAttemptDispatchObservation(const std::atomic<uint64_t>& dispatchCounter,
                                          uint64_t dispatchLimit,
                                          size_t subscriptionCount);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t logLimit, uint64_t dispatchLimit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);
    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber);
    bool TryReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                   std::atomic<uint64_t>& counter,
                                                   uint64_t limit,
                                                   uint64_t& observationNumber);
    bool TryBuildAndReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                           std::atomic<uint64_t>& counter,
                                                           uint64_t limit,
                                                           uint64_t& observationNumber,
                                                           CopiedStructureEvent& out);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
    bool TryBuildCopiedStructureEvent(const Obelisk::UE::StructureReflection::StructureInvocation& invocation,
                                      CopiedStructureEvent& out);
    size_t MaybeDispatchCopiedStructureEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::StructureReflection::StructureInvocation& invocation);
    size_t MaybeDispatchCopiedStructureEventAfterOriginal(
        bool originalWasCalled,
        const CopiedStructureEvent& event);
}
