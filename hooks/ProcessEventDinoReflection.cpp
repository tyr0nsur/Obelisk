#include "ProcessEventDinoReflection.h"

#include <cstring>

namespace Obelisk::Hooks::ProcessEventDinoReflection
{
    namespace
    {
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
            !invocation.HasParameterRanges)
        {
            return false;
        }

        out.Function = invocation.Function;

        for (const Obelisk::UE::DinoReflection::DinoFieldRange& field : invocation.Fields)
        {
            DinoScalarValue scalar;
            switch (field.Field)
            {
            case Obelisk::UE::DinoReflection::DinoField::ACharacter:
                if (field.ExposesRange || field.Range.Data || field.Range.Size != 0)
                {
                    out = {};
                    return false;
                }
                continue;
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
