#include "ProcessEventPlayerPrincipalLifecycleObserver.h"

#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleObserver
{
    namespace
    {
        constexpr int32_t kHandleNewPlayerNameIndex = 2170;
        constexpr int32_t kOnLogoutNameIndex = 2384;
        constexpr int32_t kShooterGameModeNameIndex = 9755;
        constexpr uint64_t kMaxLogLimit = 10;

        bool ParseUnsigned(const char* text, uint64_t& out)
        {
            if (!text || text[0] == '\0')
                return false;
            for (const char* cursor = text; *cursor; ++cursor)
            {
                if (*cursor < '0' || *cursor > '9')
                    return false;
            }

            errno = 0;
            char* end = nullptr;
            const unsigned long long parsed = std::strtoull(text, &end, 10);
            if (errno == ERANGE || !end || *end != '\0' ||
                parsed > std::numeric_limits<uint64_t>::max())
            {
                return false;
            }
            out = static_cast<uint64_t>(parsed);
            return true;
        }

        bool TryCopyBool(const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field,
                         LifecycleBoolObservation& out)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            switch (field.Field)
            {
            case LifecycleField::BIsFromLogin:
            case LifecycleField::ReturnValue:
                break;
            case LifecycleField::NewPlayer:
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::Exiting:
                return false;
            }

            if (!field.ExposesRange ||
                field.Redacted ||
                !field.Range.Data ||
                field.Range.Size != sizeof(uint8_t) ||
                field.Size != sizeof(uint8_t))
            {
                return false;
            }

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            if (value > 1)
                return false;

            out.Field = field.Field;
            out.Value = value != 0;
            return true;
        }

        bool AddRedactedField(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field,
                              CopiedLifecycleObservation& out)
        {
            if (out.RedactedCount >= out.RedactedStorage.size())
                return false;
            out.RedactedStorage[out.RedactedCount++] = field;
            return true;
        }

        bool AddBoolField(const LifecycleBoolObservation& value, CopiedLifecycleObservation& out)
        {
            if (out.BoolCount >= out.BoolStorage.size())
                return false;
            out.BoolStorage[out.BoolCount++] = value;
            return true;
        }

        bool TryMapPlayerPrincipalBoolField(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field,
            Obelisk::Core::PlayerPrincipalBoolField& out)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            switch (field)
            {
            case LifecycleField::BIsFromLogin:
                out = Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin;
                return true;
            case LifecycleField::ReturnValue:
                out = Obelisk::Core::PlayerPrincipalBoolField::ReturnValue;
                return true;
            case LifecycleField::NewPlayer:
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::Exiting:
                return false;
            }
            return false;
        }

        bool HasCanonicalHandleNewPlayerRedactions(const CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 3 &&
                observation.RedactedStorage[0] == LifecycleField::NewPlayer &&
                observation.RedactedStorage[1] == LifecycleField::PlayerData &&
                observation.RedactedStorage[2] == LifecycleField::PlayerCharacter;
        }

        bool HasCanonicalOnLogoutRedactions(const CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 1 &&
                observation.RedactedStorage[0] == LifecycleField::Exiting;
        }
    }

    Gate EvaluateGate(const char* enableLifecycleObserver,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256,
                      const char* logLimit,
                      const char* dispatchLimit)
    {
        if (!enableLifecycleObserver || std::strcmp(enableLifecycleObserver, "1") != 0)
            return {};

        if (!observerDebugProfileEnabled)
            return {GateStatus::MissingObserverDebugProfile, {}};
        if (!observerDebugWindowEnabled)
            return {GateStatus::MissingObserverDebugWindow, {}};
        if (!instanceMarkerEnabled)
            return {GateStatus::MissingInstanceMarker, {}};
        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};
        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        if (!logLimit || logLimit[0] == '\0')
            return {GateStatus::MissingLogLimit, binarySha256};
        uint64_t parsedLogLimit = 0;
        if (!ParseUnsigned(logLimit, parsedLogLimit))
            return {GateStatus::MalformedLogLimit, binarySha256};
        if (parsedLogLimit == 0)
            return {GateStatus::ZeroLogLimit, binarySha256};
        if (parsedLogLimit > kMaxLogLimit)
            return {GateStatus::LogLimitTooLarge, binarySha256};

        if (!dispatchLimit || dispatchLimit[0] == '\0')
            return {GateStatus::MissingDispatchLimit, binarySha256};
        uint64_t parsedDispatchLimit = 0;
        if (!ParseUnsigned(dispatchLimit, parsedDispatchLimit))
            return {GateStatus::MalformedDispatchLimit, binarySha256};
        if (parsedDispatchLimit != 0)
            return {GateStatus::NonZeroDispatchLimit, binarySha256, parsedLogLimit, parsedDispatchLimit};

        return {GateStatus::Enabled, binarySha256, parsedLogLimit, parsedDispatchLimit};
    }

    bool IsReflectedLifecycleNameIndex(int32_t nameIndex)
    {
        return nameIndex == kHandleNewPlayerNameIndex || nameIndex == kOnLogoutNameIndex;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit)
    {
        return limit != 0 && counter.load(std::memory_order_relaxed) < limit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t limit,
                                     uint64_t& observationNumber)
    {
        if (limit == 0)
        {
            observationNumber = 0;
            return false;
        }

        uint64_t current = counter.load(std::memory_order_relaxed);
        while (current < limit)
        {
            if (counter.compare_exchange_weak(current,
                                              current + 1,
                                              std::memory_order_relaxed,
                                              std::memory_order_relaxed))
            {
                observationNumber = current + 1;
                return true;
            }
        }

        observationNumber = 0;
        return false;
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return limit != 0 && observationNumber != 0 && observationNumber <= limit;
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedLifecycleNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonLifecycleFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                reader, options, function, params, invocation);
        }
        catch (...)
        {
            return {
                AttemptStatus::Rejected,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};
        if (invocation.FunctionNameIndex != nameIndex)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "player lifecycle prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t& observationNumber)
    {
        observationNumber = 0;
        if (!gate.Enabled())
            return {};

        if (!IsReflectedLifecycleNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonLifecycleFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        if (!TryReserveObservationBudget(observationCounter, gate.LogLimit, observationNumber))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        return TryIdentifyInvocation(gate, nameIndex, reader, function, params);
    }

    bool TryBuildCopiedLifecycleObservation(
        const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation,
        CopiedLifecycleObservation& out)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        out = {};
        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;

        if (invocation.OuterNameIndex != kShooterGameModeNameIndex)
            return false;

        switch (invocation.Function)
        {
        case LifecycleFunction::HandleNewPlayer:
        {
            if (invocation.FunctionNameIndex != kHandleNewPlayerNameIndex ||
                invocation.Fields.size() != 5 ||
                !invocation.HasParameterRanges)
            {
                out = {};
                return false;
            }

            bool sawBIsFromLogin = false;
            bool sawReturnValue = false;
            bool isFromLogin = false;
            bool returnValue = false;
            for (const auto& field : invocation.Fields)
            {
                switch (field.Field)
                {
                case LifecycleField::NewPlayer:
                case LifecycleField::PlayerData:
                case LifecycleField::PlayerCharacter:
                    if (!field.Redacted || field.ExposesRange || field.Range.Data != nullptr ||
                        !AddRedactedField(field.Field, out))
                    {
                        out = {};
                        return false;
                    }
                    break;
                case LifecycleField::BIsFromLogin:
                case LifecycleField::ReturnValue:
                {
                    LifecycleBoolObservation copied;
                    if (!TryCopyBool(field, copied) || !AddBoolField(copied, out))
                    {
                        out = {};
                        return false;
                    }
                    if (field.Field == LifecycleField::BIsFromLogin)
                    {
                        sawBIsFromLogin = true;
                        isFromLogin = copied.Value;
                    }
                    if (field.Field == LifecycleField::ReturnValue)
                    {
                        sawReturnValue = true;
                        returnValue = copied.Value;
                    }
                    break;
                }
                case LifecycleField::Exiting:
                    out = {};
                    return false;
                }
            }

            if (!sawBIsFromLogin || !sawReturnValue || out.RedactedCount != 3 || out.BoolCount != 2)
            {
                out = {};
                return false;
            }

            out.Role = (isFromLogin && returnValue) ? LifecycleRole::SessionStart : LifecycleRole::SessionStartRejected;
            out.Action = (isFromLogin && returnValue) ? PrincipalAction::CandidateCreated : PrincipalAction::None;
            return true;
        }
        case LifecycleFunction::OnLogout:
            if (invocation.FunctionNameIndex != kOnLogoutNameIndex ||
                invocation.Fields.size() != 1)
            {
                out = {};
                return false;
            }
            if (invocation.Fields[0].Field != LifecycleField::Exiting ||
                !invocation.Fields[0].Redacted ||
                invocation.Fields[0].ExposesRange ||
                invocation.Fields[0].Range.Data != nullptr ||
                !AddRedactedField(LifecycleField::Exiting, out))
            {
                out = {};
                return false;
            }
            out.Role = LifecycleRole::SessionEnd;
            out.Action = PrincipalAction::CandidateInvalidated;
            return true;
        }

        out = {};
        return false;
    }

    bool TryBuildCopiedLifecycleObservationAfterOriginal(bool originalWasCalled,
                                                         const Attempt& attempt,
                                                         CopiedLifecycleObservation& out)
    {
        out = {};
        if (!originalWasCalled || attempt.Status != AttemptStatus::Matched)
            return false;
        return TryBuildCopiedLifecycleObservation(attempt.Invocation, out);
    }

    bool TryMapPlayerPrincipalEventKind(LifecycleRole role,
                                        Obelisk::Core::PlayerPrincipalEventKind& out)
    {
        switch (role)
        {
        case LifecycleRole::SessionStart:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
            return true;
        case LifecycleRole::SessionStartRejected:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected;
            return true;
        case LifecycleRole::SessionEnd:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionEnd;
            return true;
        }
        return false;
    }

    bool TryMapPlayerPrincipalAction(PrincipalAction action,
                                     Obelisk::Core::PlayerPrincipalAction& out)
    {
        switch (action)
        {
        case PrincipalAction::None:
            out = Obelisk::Core::PlayerPrincipalAction::None;
            return true;
        case PrincipalAction::CandidateCreated:
            out = Obelisk::Core::PlayerPrincipalAction::CandidateCreated;
            return true;
        case PrincipalAction::CandidateInvalidated:
            out = Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated;
            return true;
        }
        return false;
    }

    bool TryBuildPlayerPrincipalEventView(
        const CopiedLifecycleObservation& observation,
        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2>& boolStorage,
        Obelisk::Core::PlayerPrincipalEventView& out)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        out = {};

        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
        if (!TryMapPlayerPrincipalEventKind(observation.Role, kind))
            return false;

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::None;
        if (!TryMapPlayerPrincipalAction(observation.Action, action))
            return false;

        switch (observation.Role)
        {
        case LifecycleRole::SessionStart:
        case LifecycleRole::SessionStartRejected:
        {
            if (observation.Function != LifecycleFunction::HandleNewPlayer ||
                observation.FunctionNameIndex != kHandleNewPlayerNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 2 ||
                !HasCanonicalHandleNewPlayerRedactions(observation))
            {
                return false;
            }

            if (observation.BoolStorage[0].Field != LifecycleField::BIsFromLogin ||
                observation.BoolStorage[1].Field != LifecycleField::ReturnValue)
            {
                return false;
            }

            const bool acceptedStart =
                observation.BoolStorage[0].Value && observation.BoolStorage[1].Value;
            if (observation.Role == LifecycleRole::SessionStart)
            {
                if (!acceptedStart ||
                    observation.Action != PrincipalAction::CandidateCreated ||
                    action != Obelisk::Core::PlayerPrincipalAction::CandidateCreated)
                {
                    return false;
                }
            }
            else
            {
                if (acceptedStart ||
                    observation.Action != PrincipalAction::None ||
                    action != Obelisk::Core::PlayerPrincipalAction::None)
                {
                    return false;
                }
            }

            for (size_t i = 0; i < observation.BoolCount; ++i)
            {
                Obelisk::Core::PlayerPrincipalBoolField mappedField =
                    Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin;
                if (!TryMapPlayerPrincipalBoolField(observation.BoolStorage[i].Field, mappedField))
                    return false;

                boolStorage[i] = {
                    .Field = mappedField,
                    .Value = observation.BoolStorage[i].Value,
                };
            }

            out = {
                .Kind = kind,
                .Action = action,
                .Bools = std::span<const Obelisk::Core::PlayerPrincipalBoolValue>(
                    boolStorage.data(),
                    observation.BoolCount),
            };
            return true;
        }
        case LifecycleRole::SessionEnd:
            if (observation.Function != LifecycleFunction::OnLogout ||
                observation.FunctionNameIndex != kOnLogoutNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 0 ||
                observation.Action != PrincipalAction::CandidateInvalidated ||
                action != Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated ||
                !HasCanonicalOnLogoutRedactions(observation))
            {
                return false;
            }

            out = {
                .Kind = kind,
                .Action = action,
                .Bools = {},
            };
            return true;
        }

        return false;
    }

    const char* LifecycleFunctionName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
        switch (function)
        {
        case LifecycleFunction::HandleNewPlayer:
            return "HandleNewPlayer";
        case LifecycleFunction::OnLogout:
            return "OnLogout";
        }
        return "Unknown";
    }

    const char* LifecycleTargetName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
        switch (function)
        {
        case LifecycleFunction::HandleNewPlayer:
            return "ShooterGameMode.HandleNewPlayer";
        case LifecycleFunction::OnLogout:
            return "ShooterGameMode.OnLogout";
        }
        return "Unknown.Unknown";
    }

    const char* LifecycleFieldName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        switch (field)
        {
        case LifecycleField::NewPlayer:
            return "NewPlayer";
        case LifecycleField::PlayerData:
            return "PlayerData";
        case LifecycleField::PlayerCharacter:
            return "PlayerCharacter";
        case LifecycleField::BIsFromLogin:
            return "bIsFromLogin";
        case LifecycleField::ReturnValue:
            return "ReturnValue";
        case LifecycleField::Exiting:
            return "Exiting";
        }
        return "Unknown";
    }

    const char* LifecycleRoleName(LifecycleRole role)
    {
        switch (role)
        {
        case LifecycleRole::SessionStart:
            return "session_start";
        case LifecycleRole::SessionEnd:
            return "session_end";
        case LifecycleRole::SessionStartRejected:
            return "session_start_rejected";
        }
        return "unknown";
    }

    const char* PrincipalActionName(PrincipalAction action)
    {
        switch (action)
        {
        case PrincipalAction::CandidateCreated:
            return "candidate_created";
        case PrincipalAction::CandidateInvalidated:
            return "candidate_invalidated";
        case PrincipalAction::None:
            return "none";
        }
        return "none";
    }
}
