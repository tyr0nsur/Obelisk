#pragma once

#include "ue/DinoReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>

namespace Obelisk::Hooks::ProcessEventDinoReflection
{
    enum class DinoScalarType
    {
        Bool,
        Int32,
    };

    enum class DinoScalarField
    {
        PassengerSeatIndex,
        BForcePassenger,
        BAllowFlyersAndWaterDinos,
        BSkipLineTrace,
    };

    struct DinoScalarValue
    {
        DinoScalarField Field = DinoScalarField::PassengerSeatIndex;
        DinoScalarType Type = DinoScalarType::Bool;
        bool BoolValue = false;
        int32_t Int32Value = 0;
    };

    struct CopiedDinoScalarObservation
    {
        Obelisk::UE::DinoReflection::DinoFunction Function =
            Obelisk::UE::DinoReflection::DinoFunction::AddPassenger;
        std::array<DinoScalarValue, 4> ScalarStorage{};
        size_t ScalarCount = 0;
    };

    bool TryBuildCopiedDinoScalarObservation(
        const Obelisk::UE::DinoReflection::DinoInvocation& invocation,
        CopiedDinoScalarObservation& out);
}
