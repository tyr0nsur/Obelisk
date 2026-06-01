#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::DinoReflection
{
    enum class DinoFunction
    {
        AddPassenger,
        AllowCarryCharacter,
    };

    enum class DinoField
    {
        ACharacter,
        PassengerSeatIndex,
        BForcePassenger,
        BAllowFlyersAndWaterDinos,
        BSkipLineTrace,
        CanCarryPawn,
        ReturnValue,
    };

    struct DinoFieldRange
    {
        DinoField Field = DinoField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct DinoInvocation
    {
        DinoFunction Function = DinoFunction::AddPassenger;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        const uint8_t* ParameterData = nullptr;
        size_t ParameterSize = 0;
        RuntimeReflection::FixedVector<DinoFieldRange, 6> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyDinoInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            DinoInvocation& out);
}
