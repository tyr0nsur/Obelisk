#include "ProcessEventStructureReflection.h"

#include <cstdint>
#include <cstring>
#include <span>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventStructureReflection
{
    Gate EvaluateGate(const char* enableStructureReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableStructureReflection || std::strcmp(enableStructureReflection, "1") != 0)
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

    bool IsNonPinCopiedScalarStructureNameIndex(int32_t nameIndex)
    {
        return Obelisk::UE::StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(nameIndex);
    }

    bool IsReflectedStructureNameIndex(int32_t nameIndex)
    {
        return nameIndex == 7541 ||
               nameIndex == 7574 ||
               nameIndex == 7605 ||
               nameIndex == 7620 ||
               nameIndex == 7636 ||
               nameIndex == 8481;
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

    bool ShouldAttemptDispatchObservation(const std::atomic<uint64_t>& dispatchCounter,
                                          uint64_t dispatchLimit,
                                          size_t subscriptionCount)
    {
        return subscriptionCount != 0 &&
               HasObservationBudgetRemaining(dispatchCounter, dispatchLimit);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && IsReflectedStructureNameIndex(nameIndex);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t logLimit, uint64_t dispatchLimit)
    {
        return ShouldAttemptRuntimeObservation(logLimit, dispatchLimit) &&
               IsReflectedStructureNameIndex(nameIndex);
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
        CopiedStructureEvent event;
        return TryBuildAndReserveDispatchBudgetForMatchedAttempt(
            attempt, counter, limit, observationNumber, event);
    }

    bool TryBuildAndReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                           std::atomic<uint64_t>& counter,
                                                           uint64_t limit,
                                                           uint64_t& observationNumber,
                                                           CopiedStructureEvent& out)
    {
        if (attempt.Status != AttemptStatus::Matched)
        {
            observationNumber = 0;
            out = {};
            return false;
        }

        if (!TryBuildCopiedStructureEvent(attempt.Invocation, out))
        {
            observationNumber = 0;
            return false;
        }

        if (!TryReserveObservationBudget(counter, limit, observationNumber))
        {
            out = {};
            return false;
        }
        return true;
    }

    bool TryBuildAndReserveDispatchBudgetForNonPinMatchedAttempt(const Attempt& attempt,
                                                                 std::atomic<uint64_t>& counter,
                                                                 uint64_t limit,
                                                                 uint64_t& observationNumber,
                                                                 CopiedStructureEvent& out)
    {
        if (attempt.Status != AttemptStatus::Matched ||
            !Obelisk::UE::StructureReflection::IsNonPinCopiedScalarFunction(attempt.Invocation.Function))
        {
            observationNumber = 0;
            out = {};
            return false;
        }

        return TryBuildAndReserveDispatchBudgetForMatchedAttempt(
            attempt, counter, limit, observationNumber, out);
    }

    namespace
    {
        Obelisk::Core::StructureEventKind ToEventKind(
            Obelisk::UE::StructureReflection::StructureFunction function)
        {
            using Obelisk::Core::StructureEventKind;
            using Obelisk::UE::StructureReflection::StructureFunction;
            switch (function)
            {
            case StructureFunction::AllowStructureAccess:
                return StructureEventKind::AllowStructureAccess;
            case StructureFunction::IsAllowedToDemolish:
                return StructureEventKind::IsAllowedToDemolish;
            case StructureFunction::SetVariant:
                return StructureEventKind::SetVariant;
            case StructureFunction::AllowToggleActivation:
                return StructureEventKind::AllowToggleActivation;
            case StructureFunction::VerifyPinCode:
                return StructureEventKind::VerifyPinCode;
            case StructureFunction::CanSeat:
                return StructureEventKind::CanSeat;
            }
            return StructureEventKind::VerifyPinCode;
        }

        bool TryGetScalarField(Obelisk::UE::StructureReflection::StructureField source,
                               Obelisk::Core::StructureScalarField& out)
        {
            using Obelisk::Core::StructureScalarField;
            using Obelisk::UE::StructureReflection::StructureField;
            switch (source)
            {
            case StructureField::VariantIndex:
                out = StructureScalarField::VariantIndex;
                return true;
            case StructureField::BForceSet:
                out = StructureScalarField::BForceSet;
                return true;
            case StructureField::BForce:
                out = StructureScalarField::BForce;
                return true;
            case StructureField::ReturnValue:
                out = StructureScalarField::ReturnValue;
                return true;
            case StructureField::ForPC:
            case StructureField::ForCharacter:
            case StructureField::PinCode:
                return false;
            }
            return false;
        }

        bool TryCopyScalar(const Obelisk::UE::StructureReflection::StructureFieldRange& field,
                           Obelisk::Core::StructureScalarValue& out)
        {
            Obelisk::Core::StructureScalarField scalarField;
            if (!TryGetScalarField(field.Field, scalarField))
                return false;
            if (!field.ExposesRange || !field.Range.Data)
                return false;
            if (field.Range.Size != field.Size)
                return false;

            out.Field = scalarField;
            if (field.Size == sizeof(int32_t))
            {
                int32_t value = 0;
                std::memcpy(&value, field.Range.Data, sizeof(value));
                out.Type = Obelisk::Core::StructureScalarType::Int32;
                out.BoolValue = false;
                out.Int32Value = value;
                return true;
            }
            if (field.Size == sizeof(uint8_t))
            {
                uint8_t value = 0;
                std::memcpy(&value, field.Range.Data, sizeof(value));
                if (value > 1)
                    return false;
                out.Type = Obelisk::Core::StructureScalarType::Bool;
                out.BoolValue = value != 0;
                out.Int32Value = 0;
                return true;
            }

            return false;
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

        if (!IsReflectedStructureNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonStructureFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::StructureReflection::StructureInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::StructureReflection::TryIdentifyStructureInvocation(
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

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    bool TryBuildCopiedStructureEvent(const Obelisk::UE::StructureReflection::StructureInvocation& invocation,
                                      CopiedStructureEvent& out)
    {
        out = {};
        out.View.Kind = ToEventKind(invocation.Function);
        out.View.FunctionNameIndex = invocation.FunctionNameIndex;
        out.View.OuterNameIndex = invocation.OuterNameIndex;

        for (const Obelisk::UE::StructureReflection::StructureFieldRange& field : invocation.Fields)
        {
            Obelisk::Core::StructureScalarField scalarField;
            if (!TryGetScalarField(field.Field, scalarField))
                continue;

            Obelisk::Core::StructureScalarValue scalar;
            if (!TryCopyScalar(field, scalar))
            {
                out = {};
                return false;
            }
            if (out.ScalarCount >= out.ScalarStorage.size())
            {
                out = {};
                return false;
            }

            out.ScalarStorage[out.ScalarCount++] = scalar;
        }

        out.View.Scalars = std::span<const Obelisk::Core::StructureScalarValue>(
            out.ScalarStorage.data(), out.ScalarCount);
        return true;
    }

    bool TryBuildNonPinCopiedStructureEvent(
        const Obelisk::UE::StructureReflection::StructureInvocation& invocation,
        CopiedStructureEvent& out)
    {
        if (!Obelisk::UE::StructureReflection::IsNonPinCopiedScalarFunction(invocation.Function))
        {
            out = {};
            return false;
        }

        return TryBuildCopiedStructureEvent(invocation, out);
    }

    namespace
    {
        bool IsSelfContainedCopiedEvent(const CopiedStructureEvent& event)
        {
            if (event.ScalarCount > event.ScalarStorage.size())
                return false;
            if (event.View.Scalars.size() != event.ScalarCount)
                return false;
            if (event.ScalarCount == 0)
                return event.View.Scalars.empty();
            return event.View.Scalars.data() == event.ScalarStorage.data();
        }

        size_t DispatchCopiedStructureEvent(const CopiedStructureEvent& event)
        {
            if (!IsSelfContainedCopiedEvent(event))
                return 0;

            return Obelisk::Core::StructureEventDispatcher::Get().Dispatch(event.View);
        }

        size_t DispatchCopiedStructureEvent(const Obelisk::UE::StructureReflection::StructureInvocation& invocation)
        {
            CopiedStructureEvent event;
            if (!TryBuildCopiedStructureEvent(invocation, event))
                return 0;

            return DispatchCopiedStructureEvent(event);
        }
    }

    size_t MaybeDispatchCopiedStructureEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::StructureReflection::StructureInvocation& invocation)
    {
        if (!originalWasCalled)
            return 0;

        return DispatchCopiedStructureEvent(invocation);
    }

    size_t MaybeDispatchCopiedStructureEventAfterOriginal(
        bool originalWasCalled,
        const CopiedStructureEvent& event)
    {
        if (!originalWasCalled)
            return 0;

        return DispatchCopiedStructureEvent(event);
    }

    size_t MaybeDispatchNonPinCopiedStructureEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::StructureReflection::StructureInvocation& invocation)
    {
        if (!originalWasCalled ||
            !Obelisk::UE::StructureReflection::IsNonPinCopiedScalarFunction(invocation.Function))
        {
            return 0;
        }

        CopiedStructureEvent event;
        if (!TryBuildNonPinCopiedStructureEvent(invocation, event))
            return 0;

        return DispatchCopiedStructureEvent(event);
    }
}
