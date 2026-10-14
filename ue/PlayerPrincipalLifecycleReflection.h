#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::UE::PlayerPrincipalLifecycleReflection
{
    enum class LifecycleFunction
    {
        CheckJoinInProgressDiagnostic,
        K2PostLoginDiagnostic,
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
        bool HasCopiedBoolValue = false;
        uint8_t CopiedBoolValue = 0;
        // Internal-only process-local correlate for redacted object fields.
        // This is Obelisk-assigned, non-persistent, not a raw UE pointer, and
        // must not be logged or exposed through the public plugin ABI.
        uint64_t ProcessLocalSubjectToken = 0;
        RuntimeReflection::ParamRange Range;
    };

    struct LifecyclePropertyFNameDrift
    {
        size_t Position = 0;
        LifecycleField Field = LifecycleField::NewPlayer;
        int32_t ExpectedNameIndex = -1;
        int32_t ObservedNameIndex = -1;
    };

    struct LifecycleInvocation
    {
        LifecycleFunction Function = LifecycleFunction::HandleNewPlayer;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        bool HasParameterRanges = false;
        bool PropertyNameIndicesMatched = false;
        bool PropertyFNameDriftDiagnosticOnly = false;
        RuntimeReflection::FixedVector<LifecycleFieldRange, 5> Fields;
        RuntimeReflection::FixedVector<LifecyclePropertyFNameDrift, 5> PropertyFNameDrifts;
    };

    enum class ProcessLocalSubjectTokenMode
    {
        Assign,
        ValidateOnly,
        MetadataOnly,
        Skip,
    };

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out);

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out,
        ProcessLocalSubjectTokenMode tokenMode);

    void ResetProcessLocalSubjectTokensForTesting();
    void SetNextProcessLocalSubjectTokenForTesting(uint64_t nextToken);
}
