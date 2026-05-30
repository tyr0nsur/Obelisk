#pragma once

#include "ue/ItemReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventItemReflection
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
        BudgetExhausted,
        NonItemFunction,
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
        Obelisk::UE::ItemReflection::ItemInvocation Invocation;
    };

    struct ItemBoolObservation
    {
        Obelisk::UE::ItemReflection::ItemField Field =
            Obelisk::UE::ItemReflection::ItemField::ReturnValue;
        bool Value = false;
    };

    struct CopiedItemObservation
    {
        Obelisk::UE::ItemReflection::ItemFunction Function =
            Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::array<ItemBoolObservation, 2> BoolStorage{};
        size_t BoolCount = 0;
    };

    Gate EvaluateGate(const char* enableItemReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedItemNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& observationCounter,
                                         uint64_t observationLimit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t observationLimit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t observationLimit);
    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t observationLimit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t observationLimit,
                                     uint64_t& observationNumber);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t observationLimit,
                                 uint64_t& observationNumber);
    bool TryBuildCopiedItemObservation(const Obelisk::UE::ItemReflection::ItemInvocation& invocation,
                                       CopiedItemObservation& out);
    bool TryBuildCopiedItemReturnObservationForMatchedAttempt(const Attempt& attempt,
                                                              CopiedItemObservation& out);
}
