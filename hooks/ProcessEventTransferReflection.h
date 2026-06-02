#pragma once

#include "ue/RuntimeReflection.h"
#include "ue/TransferReflection.h"

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventTransferReflection
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
        NonTransferFunction,
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
        Obelisk::UE::TransferReflection::TransferInvocation Invocation;
    };

    struct CopiedTransferBAcceptObservation
    {
        Obelisk::UE::TransferReflection::TransferFunction Function =
            Obelisk::UE::TransferReflection::TransferFunction::ServerTransferredPlayerConfirmationResult;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool Accepted = false;
    };

    Gate EvaluateGate(const char* enableTransferReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedTransferNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& observationCounter,
                                         uint64_t observationLimit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t observationLimit);
    bool ShouldAttemptTransferBAcceptBridgeObservation(const Gate& gate,
                                                       int32_t nameIndex,
                                                       uint64_t observationLimit,
                                                       size_t subscriberCount);
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
    bool TryBuildCopiedTransferBAcceptObservation(
        const Obelisk::UE::TransferReflection::TransferInvocation& invocation,
        CopiedTransferBAcceptObservation& out);
    bool TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(
        const Attempt& attempt,
        CopiedTransferBAcceptObservation& out);
    bool TryBuildCopiedTransferBAcceptObservationAfterOriginal(bool originalWasCalled,
                                                               const Attempt& attempt,
                                                               CopiedTransferBAcceptObservation& out);
}
