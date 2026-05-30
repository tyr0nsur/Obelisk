#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::TransferReflection
{
    enum class TransferFunction
    {
        ServerTransferredPlayerConfirmationResult,
    };

    enum class TransferField
    {
        BAccept,
    };

    struct TransferFieldRange
    {
        TransferField Field = TransferField::BAccept;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct TransferInvocation
    {
        TransferFunction Function = TransferFunction::ServerTransferredPlayerConfirmationResult;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        const uint8_t* ParameterData = nullptr;
        size_t ParameterSize = 0;
        RuntimeReflection::FixedVector<TransferFieldRange, 1> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyTransferInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                const RuntimeReflection::ReadOptions& options,
                                                                const void* function,
                                                                const void* params,
                                                                TransferInvocation& out);
}
