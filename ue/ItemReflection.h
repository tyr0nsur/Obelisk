#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::ItemReflection
{
    enum class ItemFunction
    {
        AllowEquipItem,
        CanRepair,
        CraftBlueprint,
        UseItemOntoItem,
    };

    enum class ItemField
    {
        ToInventory,
        BIgnoreInventoryRequirement,
        BConsumeResources,
        DestinationItem,
        AdditionalData,
        ReturnValue,
    };

    struct ItemFieldRange
    {
        ItemField Field = ItemField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct ItemInvocation
    {
        ItemFunction Function = ItemFunction::AllowEquipItem;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        RuntimeReflection::FixedVector<ItemFieldRange, 3> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyItemInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            ItemInvocation& out);
}
