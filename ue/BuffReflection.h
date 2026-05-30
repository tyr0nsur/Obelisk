#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::BuffReflection
{
    enum class BuffFunction
    {
        AllowPostProcessEffect,
        BPBuffPreventUploading,
        BPOnBuffLifetimeUpdated,
        BuffOverrideInventoryAccessInput,
        BPCustomAllowAddBuff,
        BPPreventAddingOtherBuff,
    };

    enum class BuffField
    {
        InController,
        BInputPressed,
        ForCharacter,
        DamageCauser,
        AnotherBuffClass,
        ReturnValue,
    };

    struct BuffFieldRange
    {
        BuffField Field = BuffField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t PropertyClassNameIndex = -1;
        int32_t PropertyClassObjectIndex = -1;
        uint64_t PropertyFlags = 0;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct BuffInvocation
    {
        BuffFunction Function = BuffFunction::AllowPostProcessEffect;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        const uint8_t* ParameterData = nullptr;
        size_t ParameterSize = 0;
        RuntimeReflection::FixedVector<BuffFieldRange, 4> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyBuffInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            BuffInvocation& out);
}
