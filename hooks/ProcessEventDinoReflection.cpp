#include "ProcessEventDinoReflection.h"

#include <array>
#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventDinoReflection
{
    Gate EvaluateGate(const char* enableDinoReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableDinoReflection || std::strcmp(enableDinoReflection, "1") != 0)
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

    bool IsReflectedDinoNameIndex(int32_t nameIndex)
    {
        return nameIndex == 8267 || nameIndex == 8269;
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
            IsReflectedDinoNameIndex(nameIndex);
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
        constexpr int32_t kAddPassengerNameIndex = 8267;
        constexpr int32_t kAllowCarryCharacterNameIndex = 8269;
        constexpr int32_t kPrimalDinoCharacterNameIndex = 8265;
        constexpr int32_t kACharacterNameIndex = 4044;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBSkipLineTraceNameIndex = 25580;
        constexpr int32_t kBAllowFlyersAndWaterDinosNameIndex = 25581;
        constexpr int32_t kBForcePassengerNameIndex = 25582;
        constexpr int32_t kPassengerSeatIndexNameIndex = 25583;

        struct ExpectedDinoField
        {
            Obelisk::UE::DinoReflection::DinoField Field;
            int32_t PropertyNameIndex = -1;
            int32_t Offset = -1;
            size_t Size = 0;
            bool ExposesRange = false;
        };

        constexpr std::array<ExpectedDinoField, 6> kAddPassengerFields{{
            {Obelisk::UE::DinoReflection::DinoField::ACharacter, kACharacterNameIndex, 0x00, 0x08, false},
            {Obelisk::UE::DinoReflection::DinoField::PassengerSeatIndex,
             kPassengerSeatIndexNameIndex,
             0x08,
             0x04,
             true},
            {Obelisk::UE::DinoReflection::DinoField::BForcePassenger,
             kBForcePassengerNameIndex,
             0x0c,
             0x01,
             true},
            {Obelisk::UE::DinoReflection::DinoField::BAllowFlyersAndWaterDinos,
             kBAllowFlyersAndWaterDinosNameIndex,
             0x0d,
             0x01,
             true},
            {Obelisk::UE::DinoReflection::DinoField::BSkipLineTrace,
             kBSkipLineTraceNameIndex,
             0x0e,
             0x01,
             true},
            {Obelisk::UE::DinoReflection::DinoField::ReturnValue,
             kReturnValueNameIndex,
             0x0f,
             0x01,
             false},
        }};

        bool MatchesExpectedField(const Obelisk::UE::DinoReflection::DinoFieldRange& field,
                                  const ExpectedDinoField& expected)
        {
            return field.Field == expected.Field &&
                field.PropertyNameIndex == expected.PropertyNameIndex &&
                field.Offset == expected.Offset &&
                field.Size == expected.Size &&
                field.ExposesRange == expected.ExposesRange;
        }

        bool MatchesExpectedParamRange(
            const Obelisk::UE::DinoReflection::DinoInvocation& invocation,
            const Obelisk::UE::DinoReflection::DinoFieldRange& field,
            const ExpectedDinoField& expected)
        {
            if (!invocation.HasParameterRanges ||
                !invocation.ParameterData ||
                expected.Offset < 0 ||
                expected.Size > invocation.ParameterSize)
            {
                return false;
            }

            const size_t offset = static_cast<size_t>(expected.Offset);
            if (offset > invocation.ParameterSize ||
                expected.Size > invocation.ParameterSize - offset)
            {
                return false;
            }

            return field.Range.Data == invocation.ParameterData + offset &&
                field.Range.Size == expected.Size;
        }

        bool TryCopyInt32(const Obelisk::UE::DinoReflection::DinoFieldRange& field,
                          DinoScalarField scalarField,
                          DinoScalarValue& out)
        {
            if (!field.ExposesRange ||
                !field.Range.Data ||
                field.Size != sizeof(int32_t) ||
                field.Range.Size != sizeof(int32_t))
            {
                return false;
            }

            int32_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            out = {
                .Field = scalarField,
                .Type = DinoScalarType::Int32,
                .BoolValue = false,
                .Int32Value = value,
            };
            return true;
        }

        bool TryCopyBool(const Obelisk::UE::DinoReflection::DinoFieldRange& field,
                         DinoScalarField scalarField,
                         DinoScalarValue& out)
        {
            if (!field.ExposesRange ||
                !field.Range.Data ||
                field.Size != sizeof(uint8_t) ||
                field.Range.Size != sizeof(uint8_t))
            {
                return false;
            }

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            if (value > 1)
                return false;

            out = {
                .Field = scalarField,
                .Type = DinoScalarType::Bool,
                .BoolValue = value != 0,
                .Int32Value = 0,
            };
            return true;
        }

        bool AddScalar(CopiedDinoScalarObservation& out, const DinoScalarValue& scalar)
        {
            if (out.ScalarCount >= out.ScalarStorage.size())
                return false;

            out.ScalarStorage[out.ScalarCount++] = scalar;
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

        if (!IsReflectedDinoNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonDinoFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::DinoReflection::DinoInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::DinoReflection::TryIdentifyDinoInvocation(
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
                    "dino prefilter FName does not match reflected UFunction FName"),
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

        if (!IsReflectedDinoNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonDinoFunction,
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

    bool TryBuildCopiedDinoScalarObservation(
        const Obelisk::UE::DinoReflection::DinoInvocation& invocation,
        CopiedDinoScalarObservation& out)
    {
        out = {};
        if (invocation.Function != Obelisk::UE::DinoReflection::DinoFunction::AddPassenger ||
            invocation.FunctionNameIndex != kAddPassengerNameIndex ||
            invocation.OuterNameIndex != kPrimalDinoCharacterNameIndex ||
            !invocation.HasParameterRanges)
        {
            return false;
        }

        if (invocation.Fields.size() != kAddPassengerFields.size())
            return false;

        out.Function = invocation.Function;

        for (size_t fieldIndex = 0; fieldIndex < invocation.Fields.size(); ++fieldIndex)
        {
            const Obelisk::UE::DinoReflection::DinoFieldRange& field = invocation.Fields[fieldIndex];
            const ExpectedDinoField& expectedField = kAddPassengerFields[fieldIndex];
            if (!MatchesExpectedField(field, expectedField))
            {
                out = {};
                return false;
            }

            if (!expectedField.ExposesRange)
            {
                if (field.Range.Data || field.Range.Size != 0)
                {
                    out = {};
                    return false;
                }
                continue;
            }

            if (!MatchesExpectedParamRange(invocation, field, expectedField))
            {
                out = {};
                return false;
            }

            DinoScalarValue scalar;
            switch (field.Field)
            {
            case Obelisk::UE::DinoReflection::DinoField::ACharacter:
                out = {};
                return false;
            case Obelisk::UE::DinoReflection::DinoField::PassengerSeatIndex:
                if (!TryCopyInt32(field, DinoScalarField::PassengerSeatIndex, scalar) ||
                    !AddScalar(out, scalar))
                {
                    out = {};
                    return false;
                }
                continue;
            case Obelisk::UE::DinoReflection::DinoField::BForcePassenger:
                if (!TryCopyBool(field, DinoScalarField::BForcePassenger, scalar) ||
                    !AddScalar(out, scalar))
                {
                    out = {};
                    return false;
                }
                continue;
            case Obelisk::UE::DinoReflection::DinoField::BAllowFlyersAndWaterDinos:
                if (!TryCopyBool(field, DinoScalarField::BAllowFlyersAndWaterDinos, scalar) ||
                    !AddScalar(out, scalar))
                {
                    out = {};
                    return false;
                }
                continue;
            case Obelisk::UE::DinoReflection::DinoField::BSkipLineTrace:
                if (!TryCopyBool(field, DinoScalarField::BSkipLineTrace, scalar) ||
                    !AddScalar(out, scalar))
                {
                    out = {};
                    return false;
                }
                continue;
            case Obelisk::UE::DinoReflection::DinoField::ReturnValue:
                continue;
            case Obelisk::UE::DinoReflection::DinoField::CanCarryPawn:
                out = {};
                return false;
            }
        }

        if (out.ScalarCount != out.ScalarStorage.size())
        {
            out = {};
            return false;
        }

        return true;
    }

    bool TryBuildCopiedDinoScalarObservationForMatchedAttempt(
        const Attempt& attempt,
        CopiedDinoScalarObservation& out)
    {
        out = {};
        if (attempt.Status != AttemptStatus::Matched)
            return false;

        return TryBuildCopiedDinoScalarObservation(attempt.Invocation, out);
    }
}
