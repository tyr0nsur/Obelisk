#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::MissionReflection
{
    enum class MissionFunction
    {
        GetPlayerUsableItems,
        AddPlayerToMission,
        BPAllowPlayerToLeaveMission,
        BPOnPlayerRemovedFromMission,
    };

    enum class MissionField
    {
        Character,
        OutItemIDs,
        PlayerCharacter,
        BForceAdd,
        PlayerPawn,
        Player,
        Controller,
        BFromMissionCompleteEvent,
        BLastPhaseSuccess,
        ReturnValue,
    };

    struct MissionFieldRange
    {
        MissionField Field = MissionField::ReturnValue;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct MissionInvocation
    {
        MissionFunction Function = MissionFunction::GetPlayerUsableItems;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        RuntimeReflection::FixedVector<MissionFieldRange, 4> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyMissionInvocation(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::ReadOptions& options,
                                                               const void* function,
                                                               const void* params,
                                                               MissionInvocation& out);
}
