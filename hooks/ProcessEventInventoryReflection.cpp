#include "ProcessEventInventoryReflection.h"

#include <cstdint>
#include <cstring>
#include <span>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventInventoryReflection
{
    Gate EvaluateGate(const char* enableInventoryReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableInventoryReflection || std::strcmp(enableInventoryReflection, "1") != 0)
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

    bool IsReflectedInventoryNameIndex(int32_t nameIndex)
    {
        return nameIndex == 6236 || nameIndex == 6252;
    }

    bool ShouldAttemptObservation(uint64_t limit)
    {
        return limit != 0;
    }

    bool ShouldAttemptRuntimeObservation(uint64_t logLimit, uint64_t dispatchLimit)
    {
        return ShouldAttemptObservation(logLimit) || ShouldAttemptObservation(dispatchLimit);
    }

    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& logCounter,
                                         uint64_t logLimit,
                                         const std::atomic<uint64_t>& dispatchCounter,
                                         uint64_t dispatchLimit)
    {
        return HasObservationBudgetRemaining(logCounter, logLimit) ||
               HasObservationBudgetRemaining(dispatchCounter, dispatchLimit);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && IsReflectedInventoryNameIndex(nameIndex);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t logLimit, uint64_t dispatchLimit)
    {
        return ShouldAttemptRuntimeObservation(logLimit, dispatchLimit) &&
               IsReflectedInventoryNameIndex(nameIndex);
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && observationNumber != 0 && observationNumber <= limit;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && counter.load() < limit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber)
    {
        if (!ShouldAttemptObservation(limit))
        {
            observationNumber = 0;
            return false;
        }
        uint64_t current = counter.load();
        while (current < limit)
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

    bool TryReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                   std::atomic<uint64_t>& counter,
                                                   uint64_t limit,
                                                   uint64_t& observationNumber)
    {
        if (attempt.Status != AttemptStatus::Matched)
        {
            observationNumber = 0;
            return false;
        }
        return TryReserveObservationBudget(counter, limit, observationNumber);
    }

    namespace
    {
        Obelisk::Core::InventoryPolicyEventKind ToEventKind(
            Obelisk::UE::InventoryReflection::InventoryFunction function)
        {
            using Obelisk::Core::InventoryPolicyEventKind;
            using Obelisk::UE::InventoryReflection::InventoryFunction;
            switch (function)
            {
            case InventoryFunction::AllowRemoteAddToInventory:
                return InventoryPolicyEventKind::AllowRemoteAddToInventory;
            case InventoryFunction::CanUse:
                return InventoryPolicyEventKind::CanUse;
            }
            return InventoryPolicyEventKind::CanUse;
        }

        bool TryGetScalarField(Obelisk::UE::InventoryReflection::InventoryField source,
                               Obelisk::Core::InventoryPolicyScalarField& out)
        {
            using Obelisk::Core::InventoryPolicyScalarField;
            using Obelisk::UE::InventoryReflection::InventoryField;
            switch (source)
            {
            case InventoryField::BRequestedByPlayer:
                out = InventoryPolicyScalarField::BRequestedByPlayer;
                return true;
            case InventoryField::BIgnoreCooldown:
                out = InventoryPolicyScalarField::BIgnoreCooldown;
                return true;
            case InventoryField::ReturnValue:
                out = InventoryPolicyScalarField::ReturnValue;
                return true;
            case InventoryField::InventoryComponent:
            case InventoryField::ByPC:
                return false;
            }
            return false;
        }

        bool TryCopyScalar(const Obelisk::UE::InventoryReflection::InventoryFieldRange& field,
                           Obelisk::Core::InventoryPolicyScalarValue& out)
        {
            Obelisk::Core::InventoryPolicyScalarField scalarField;
            if (!TryGetScalarField(field.Field, scalarField))
                return false;
            if (!field.ExposesRange || !field.Range.Data || field.Size != sizeof(uint8_t))
                return false;

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            out.Field = scalarField;
            out.BoolValue = value != 0;
            return true;
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

        if (!IsReflectedInventoryNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonInventoryFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::InventoryReflection::InventoryInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result =
            Obelisk::UE::InventoryReflection::TryIdentifyInventoryInvocation(
                reader, options, function, params, invocation);
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    bool TryBuildCopiedInventoryPolicyEvent(
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation,
        CopiedInventoryPolicyEvent& out)
    {
        out = {};
        out.View.Kind = ToEventKind(invocation.Function);

        for (const Obelisk::UE::InventoryReflection::InventoryFieldRange& field : invocation.Fields)
        {
            Obelisk::Core::InventoryPolicyScalarValue scalar;
            if (!TryCopyScalar(field, scalar))
                continue;
            if (out.ScalarCount >= out.ScalarStorage.size())
                return false;

            out.ScalarStorage[out.ScalarCount++] = scalar;
        }

        out.View.Scalars = std::span<const Obelisk::Core::InventoryPolicyScalarValue>(
            out.ScalarStorage.data(), out.ScalarCount);
        return true;
    }

    namespace
    {
        size_t DispatchCopiedInventoryPolicyEvent(
            const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation)
        {
            CopiedInventoryPolicyEvent event;
            if (!TryBuildCopiedInventoryPolicyEvent(invocation, event))
                return 0;

            return Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(event.View);
        }
    }

    size_t MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation)
    {
        if (!originalWasCalled)
            return 0;

        return DispatchCopiedInventoryPolicyEvent(invocation);
    }
}
