#include "ProcessEventTransferReflection.h"

#include <cstdint>
#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventTransferReflection
{
    Gate EvaluateGate(const char* enableTransferReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableTransferReflection || std::strcmp(enableTransferReflection, "1") != 0)
            return {};

        if (!observerDebugProfileEnabled)
            return {GateStatus::MissingObserverDebugProfile, {}};

        if (!observerDebugWindowEnabled)
            return {GateStatus::MissingObserverDebugWindow, {}};

        if (!instanceMarkerEnabled)
            return {GateStatus::MissingInstanceMarker, {}};

        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};

        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        return {GateStatus::Enabled, binarySha256};
    }

    bool IsReflectedTransferNameIndex(int32_t nameIndex)
    {
        return nameIndex == 2759;
    }

    bool ShouldAttemptObservation(uint64_t observationLimit)
    {
        return observationLimit != 0;
    }

    bool ShouldAttemptRuntimeObservation(uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit);
    }

    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& observationCounter,
                                         uint64_t observationLimit)
    {
        return HasObservationBudgetRemaining(observationCounter, observationLimit);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t observationLimit)
    {
        return ShouldAttemptRuntimeObservation(observationLimit) &&
               IsReflectedTransferNameIndex(nameIndex);
    }

    bool ShouldAttemptTransferBAcceptBridgeObservation(const Gate& gate,
                                                       int32_t nameIndex,
                                                       uint64_t observationLimit,
                                                       size_t subscriberCount)
    {
        return gate.Enabled() &&
               subscriberCount != 0 &&
               ShouldAttemptRuntimeObservation(observationLimit) &&
               IsReflectedTransferNameIndex(nameIndex);
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit) &&
               observationNumber != 0 &&
               observationNumber <= observationLimit;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit) && counter.load() < observationLimit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t observationLimit,
                                     uint64_t& observationNumber)
    {
        if (!ShouldAttemptObservation(observationLimit))
        {
            observationNumber = 0;
            return false;
        }

        uint64_t current = counter.load();
        while (current < observationLimit)
        {
            if (counter.compare_exchange_weak(current, current + 1))
            {
                observationNumber = current + 1;
                return true;
            }
        }

        observationNumber = 0;
        return false;
    }

    namespace
    {
        constexpr int32_t kServerTransferredPlayerConfirmationResultNameIndex = 2759;
        constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
        constexpr int32_t kBAcceptNameIndex = 21480;
        constexpr size_t kBAcceptSize = 1;

        bool MatchesExpectedParamRange(
            const Obelisk::UE::TransferReflection::TransferInvocation& invocation,
            const Obelisk::UE::TransferReflection::TransferFieldRange& field)
        {
            if (!invocation.HasParameterRanges ||
                !invocation.ParameterData ||
                invocation.ParameterSize != kBAcceptSize ||
                field.Offset != 0 ||
                field.Size != kBAcceptSize)
            {
                return false;
            }

            return field.Range.Data == invocation.ParameterData &&
                   field.Range.Size == kBAcceptSize;
        }
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedTransferNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonTransferFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::TransferReflection::TransferInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::TransferReflection::TryIdentifyTransferInvocation(
                reader, options, function, params, invocation);
        }
        catch (...)
        {
            return {
                AttemptStatus::Rejected,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};
        if (invocation.FunctionNameIndex != nameIndex)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "transfer prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t observationLimit,
                                 uint64_t& observationNumber)
    {
        observationNumber = 0;
        if (!gate.Enabled())
            return {};

        if (!IsReflectedTransferNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonTransferFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        if (!TryReserveObservationBudget(observationCounter, observationLimit, observationNumber))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        return TryIdentifyInvocation(gate, nameIndex, reader, function, params);
    }

    bool TryBuildCopiedTransferBAcceptObservation(
        const Obelisk::UE::TransferReflection::TransferInvocation& invocation,
        CopiedTransferBAcceptObservation& out)
    {
        out = {};
        if (invocation.Function !=
                Obelisk::UE::TransferReflection::TransferFunction::ServerTransferredPlayerConfirmationResult ||
            invocation.FunctionNameIndex != kServerTransferredPlayerConfirmationResultNameIndex ||
            invocation.OuterNameIndex != kShooterPlayerControllerNameIndex ||
            invocation.Fields.size() != 1)
        {
            return false;
        }

        const Obelisk::UE::TransferReflection::TransferFieldRange& field = invocation.Fields[0];
        if (field.Field != Obelisk::UE::TransferReflection::TransferField::BAccept ||
            field.PropertyNameIndex != kBAcceptNameIndex ||
            !field.ExposesRange ||
            !MatchesExpectedParamRange(invocation, field))
        {
            return false;
        }

        uint8_t value = 0;
        std::memcpy(&value, field.Range.Data, sizeof(value));
        if (value > 1)
            return false;

        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;
        out.Accepted = value != 0;
        return true;
    }

    bool TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(
        const Attempt& attempt,
        CopiedTransferBAcceptObservation& out)
    {
        out = {};
        if (attempt.Status != AttemptStatus::Matched)
            return false;

        return TryBuildCopiedTransferBAcceptObservation(attempt.Invocation, out);
    }

    bool TryBuildCopiedTransferBAcceptObservationAfterOriginal(bool originalWasCalled,
                                                               const Attempt& attempt,
                                                               CopiedTransferBAcceptObservation& out)
    {
        out = {};
        if (!originalWasCalled)
            return false;

        return TryBuildCopiedTransferBAcceptObservationForMatchedAttempt(attempt, out);
    }
}
