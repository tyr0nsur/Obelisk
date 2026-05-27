#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::InventoryReflection
{
    enum class InventoryFunction
    {
        AllowRemoteAddToInventory,
        CanUse,
    };

    enum class InventoryField
    {
        InventoryComponent,
        ByPC,
        BRequestedByPlayer,
        BIgnoreCooldown,
        ReturnValue,
    };

    struct InventoryFieldRange
    {
        InventoryField Field = InventoryField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct InventoryInvocation
    {
        InventoryFunction Function = InventoryFunction::CanUse;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        RuntimeReflection::FixedVector<InventoryFieldRange, 4> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyInventoryInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                 const RuntimeReflection::ReadOptions& options,
                                                                 const void* function,
                                                                 const void* params,
                                                                 InventoryInvocation& out);
}
