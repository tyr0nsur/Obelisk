#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::StructureReflection
{
    enum class StructureFunction
    {
        VerifyPinCode,
        AllowToggleActivation,
        CanSeat,
        SetVariant,
        AllowStructureAccess,
        IsAllowedToDemolish,
    };

    enum class StructureField
    {
        ForPC,
        ForCharacter,
        PinCode,
        VariantIndex,
        BForceSet,
        BForce,
        ReturnValue,
    };

    struct StructureFieldRange
    {
        StructureField Field = StructureField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool Sensitive = false;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct StructureInvocation
    {
        StructureFunction Function = StructureFunction::VerifyPinCode;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        RuntimeReflection::FixedVector<StructureFieldRange, 6> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyStructureInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                 const RuntimeReflection::ReadOptions& options,
                                                                 const void* function,
                                                                 const void* params,
                                                                 StructureInvocation& out);
}
