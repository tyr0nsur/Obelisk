#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::PlayerPrincipalLifecycleReflection
{
    enum class LifecycleFunction
    {
        HandleNewPlayer,
        OnLogout,
    };

    enum class LifecycleField
    {
        NewPlayer,
        PlayerData,
        PlayerCharacter,
        BIsFromLogin,
        ReturnValue,
        Exiting,
    };

    struct LifecycleFieldRange
    {
        LifecycleField Field = LifecycleField::NewPlayer;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        bool Redacted = true;
        RuntimeReflection::ParamRange Range;
    };

    struct LifecycleInvocation
    {
        LifecycleFunction Function = LifecycleFunction::HandleNewPlayer;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        RuntimeReflection::FixedVector<LifecycleFieldRange, 5> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out);
}
