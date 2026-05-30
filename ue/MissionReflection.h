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
        // Internal SHA-scoped metadata guardrail only. This is not public identity
        // and must not be logged or exposed as a Mission SDK payload field.
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        bool ExposesRange = false;
        RuntimeReflection::ParamRange Range;
    };

    struct MissionInvocation
    {
        MissionFunction Function = MissionFunction::GetPlayerUsableItems;
        // Internal matcher sentinels only. These FName indices are not stable
        // identity, public API, or observer log fields.
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        // Borrowed params provenance for immediate copied-bool validation only.
        // Do not persist, mutate through, log, expose to plugins, or treat as
        // raw Mission payload access.
        const uint8_t* ParameterData = nullptr;
        size_t ParameterSize = 0;
        RuntimeReflection::FixedVector<MissionFieldRange, 4> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyMissionInvocation(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::ReadOptions& options,
                                                               const void* function,
                                                               const void* params,
                                                               MissionInvocation& out);
}
