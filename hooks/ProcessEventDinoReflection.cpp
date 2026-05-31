#include "ProcessEventDinoReflection.h"

#include <array>
#include <cstring>

namespace Obelisk::Hooks::ProcessEventDinoReflection
{
    namespace
    {
        constexpr int32_t kAddPassengerNameIndex = 8267;
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

            if (!field.Range.Data || field.Range.Size != field.Size)
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
}
