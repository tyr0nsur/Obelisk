#include "hooks/ProcessEventPlayerPrincipalLifecycleObserver.h"

#include <atomic>
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace
{
    using namespace Obelisk::Hooks;
    using namespace Obelisk::UE::PlayerPrincipalLifecycleReflection;
    using namespace Obelisk::UE::RuntimeReflection;
    namespace Observer = ProcessEventPlayerPrincipalLifecycleObserver;

    constexpr const char* kSupportedSha =
        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520";
    constexpr int32_t kHandleNewPlayerNameIndex = 2170;
    constexpr int32_t kOnLogoutNameIndex = 2384;
    constexpr int32_t kShooterGameModeNameIndex = 9755;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kPlayerDataNameIndex = 21307;
    constexpr int32_t kPlayerCharacterNameIndex = 22961;
    constexpr int32_t kNewPlayerNameIndex = 28411;
    constexpr int32_t kBIsFromLoginNameIndex = 28509;
    constexpr int32_t kExitingNameIndex = 28543;

    static_assert(std::is_standard_layout_v<Observer::LifecycleBoolObservation>,
                  "copied player lifecycle bool observations must keep a simple layout");
    static_assert(std::is_trivially_copyable_v<Observer::LifecycleBoolObservation>,
                  "copied player lifecycle bool observations must remain byte-copyable");
    static_assert(std::is_standard_layout_v<Observer::CopiedLifecycleObservation>,
                  "copied player lifecycle observations must keep a simple layout");
    static_assert(std::is_trivially_copyable_v<Observer::CopiedLifecycleObservation>,
                  "copied player lifecycle observations must remain byte-copyable");

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("reader should not be called");
    }

    Observer::Gate EnabledGate(const char* logLimit = "10", const char* dispatchLimit = "0")
    {
        return Observer::EvaluateGate("1", true, true, true, kSupportedSha, logLimit, dispatchLimit);
    }

    LifecycleFieldRange RedactedField(LifecycleField field, int32_t nameIndex, int32_t offset, size_t size)
    {
        LifecycleFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = nameIndex;
        value.Offset = offset;
        value.Size = size;
        value.ExposesRange = false;
        value.Redacted = true;
        return value;
    }

    LifecycleFieldRange BoolField(LifecycleField field, int32_t nameIndex, int32_t offset, const uint8_t* source)
    {
        LifecycleFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = nameIndex;
        value.Offset = offset;
        value.Size = sizeof(uint8_t);
        value.ExposesRange = true;
        value.Redacted = false;
        value.Range = {source, sizeof(uint8_t)};
        return value;
    }

    LifecycleInvocation HandleNewPlayerInvocation(uint8_t isFromLogin, uint8_t returnValue)
    {
        static uint8_t values[2] = {};
        values[0] = isFromLogin;
        values[1] = returnValue;

        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::HandleNewPlayer;
        invocation.FunctionNameIndex = kHandleNewPlayerNameIndex;
        invocation.OuterNameIndex = kShooterGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(RedactedField(LifecycleField::NewPlayer, kNewPlayerNameIndex, 0x00, 0x08));
        invocation.Fields.push_back(RedactedField(LifecycleField::PlayerData, kPlayerDataNameIndex, 0x08, 0x08));
        invocation.Fields.push_back(RedactedField(LifecycleField::PlayerCharacter,
                                                 kPlayerCharacterNameIndex,
                                                 0x10,
                                                 0x08));
        invocation.Fields.push_back(BoolField(LifecycleField::BIsFromLogin,
                                             kBIsFromLoginNameIndex,
                                             0x18,
                                             &values[0]));
        invocation.Fields.push_back(BoolField(LifecycleField::ReturnValue,
                                             kReturnValueNameIndex,
                                             0x19,
                                             &values[1]));
        return invocation;
    }

    LifecycleInvocation OnLogoutInvocation()
    {
        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::OnLogout;
        invocation.FunctionNameIndex = kOnLogoutNameIndex;
        invocation.OuterNameIndex = kShooterGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(RedactedField(LifecycleField::Exiting, kExitingNameIndex, 0x00, 0x08));
        return invocation;
    }

    void RequirePlayerPrincipalEventView(
        const Observer::CopiedLifecycleObservation& observation,
        Obelisk::Core::PlayerPrincipalEventKind expectedKind,
        Obelisk::Core::PlayerPrincipalAction expectedAction,
        size_t expectedBoolCount,
        const char* message)
    {
        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event), message);
        Require(event.Kind == expectedKind, message);
        Require(event.Action == expectedAction, message);
        Require(event.Bools.size() == expectedBoolCount, message);
        if (expectedBoolCount != 0)
            Require(event.Bools.data() == boolStorage.data(), message);
        else
            Require(event.Bools.empty(), message);
    }

    void TestGateMatrix()
    {
        Require(Observer::EvaluateGate(nullptr, true, true, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::Disabled,
                "missing enable should disable gate");
        Require(Observer::EvaluateGate("1", false, true, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingObserverDebugProfile,
                "missing observer profile accepted");
        Require(Observer::EvaluateGate("1", true, false, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingObserverDebugWindow,
                "missing observer window accepted");
        Require(Observer::EvaluateGate("1", true, true, false, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingInstanceMarker,
                "missing observer marker accepted");
        Require(Observer::EvaluateGate("1", true, true, true, nullptr, "1", "0").Status ==
                    Observer::GateStatus::MissingBinarySha256,
                "missing sha accepted");
        Require(Observer::EvaluateGate("1",
                                       true,
                                       true,
                                       true,
                                       "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                                       "1",
                                       "0")
                    .Status == Observer::GateStatus::UnsupportedBinarySha256,
                "unsupported sha accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, nullptr, "0").Status ==
                    Observer::GateStatus::MissingLogLimit,
                "missing log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "abc", "0").Status ==
                    Observer::GateStatus::MalformedLogLimit,
                "malformed log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "0", "0").Status ==
                    Observer::GateStatus::ZeroLogLimit,
                "zero log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "11", "0").Status ==
                    Observer::GateStatus::LogLimitTooLarge,
                "oversized log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", nullptr).Status ==
                    Observer::GateStatus::MissingDispatchLimit,
                "missing dispatch limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", "x").Status ==
                    Observer::GateStatus::MalformedDispatchLimit,
                "malformed dispatch limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", "1").Status ==
                    Observer::GateStatus::NonZeroDispatchLimit,
                "non-zero dispatch limit accepted");

        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "valid lifecycle gate not enabled");
        Require(gate.LogLimit == 10, "lifecycle log limit mismatch");
        Require(gate.DispatchLimit == 0, "lifecycle dispatch limit mismatch");
    }

    void TestNameAndBudgetPrefilters()
    {
        Require(Observer::IsReflectedLifecycleNameIndex(kHandleNewPlayerNameIndex),
                "HandleNewPlayer name index rejected");
        Require(Observer::IsReflectedLifecycleNameIndex(kOnLogoutNameIndex),
                "OnLogout name index rejected");
        Require(!Observer::IsReflectedLifecycleNameIndex(9999), "non-lifecycle name index accepted");

        std::atomic<uint64_t> counter{0};
        uint64_t number = 0;
        Require(Observer::TryReserveObservationBudget(counter, 2, number), "first reserve failed");
        Require(number == 1, "first reserve number mismatch");
        Require(Observer::TryReserveObservationBudget(counter, 2, number), "second reserve failed");
        Require(number == 2, "second reserve number mismatch");
        Require(!Observer::TryReserveObservationBudget(counter, 2, number), "budget overflow accepted");
        Require(number == 0, "budget overflow number was not cleared");
        Require(!Observer::ShouldLogObservation(0, 2), "zero observation was loggable");
        Require(Observer::ShouldLogObservation(2, 2), "bounded observation was not loggable");
        Require(!Observer::ShouldLogObservation(3, 2), "over-budget observation was loggable");
    }

    void TestTryIdentifyFastPathsDoNotRead()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Observer::Attempt attempt = Observer::TryIdentifyInvocation(
            {}, kHandleNewPlayerNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::Disabled, "disabled gate did not short-circuit");

        attempt = Observer::TryIdentifyInvocation(
            EnabledGate(), 9999, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "non-lifecycle FName did not short-circuit");

        attempt = Observer::TryIdentifyInvocation(
            EnabledGate(), kHandleNewPlayerNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::Rejected, "reader exception was not rejected");
    }

    void TestBuildsHandleNewPlayerObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "valid HandleNewPlayer observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStart, "session start role mismatch");
        Require(observation.Action == Observer::PrincipalAction::CandidateCreated,
                "candidate-created action mismatch");
        Require(observation.BoolCount == 2, "HandleNewPlayer bool count mismatch");
        Require(observation.RedactedCount == 3, "HandleNewPlayer redacted count mismatch");
        Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin, "first bool field mismatch");
        Require(observation.BoolStorage[0].Value, "bIsFromLogin bool value mismatch");
        Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue, "second bool field mismatch");
        Require(observation.BoolStorage[1].Value, "ReturnValue bool value mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "rejected session observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "session_start_rejected role mismatch");
        Require(observation.Action == Observer::PrincipalAction::None,
                "session_start_rejected action mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(0, 1), observation),
                "non-login HandleNewPlayer observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "non-login session_start_rejected role mismatch");
        Require(observation.Action == Observer::PrincipalAction::None,
                "non-login session_start_rejected action mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(0, 0), observation),
                "non-login rejected HandleNewPlayer observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "non-login rejected session_start_rejected role mismatch");
        Require(observation.Action == Observer::PrincipalAction::None,
                "non-login rejected session_start_rejected action mismatch");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(2, 1), observation),
                "non-canonical lifecycle bool accepted");
        Require(observation.BoolCount == 0, "failed lifecycle copy left bools");
    }

    void TestBuildsOnLogoutObservationWithoutIdentity()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "valid OnLogout observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionEnd, "session end role mismatch");
        Require(observation.Action == Observer::PrincipalAction::CandidateInvalidated,
                "candidate invalidated action mismatch");
        Require(observation.BoolCount == 0, "OnLogout copied bools");
        Require(observation.RedactedCount == 1, "OnLogout redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::Exiting, "OnLogout redacted field mismatch");
    }

    void TestAfterOriginalGuard()
    {
        Observer::Attempt attempt;
        attempt.Status = Observer::AttemptStatus::Matched;
        attempt.Invocation = HandleNewPlayerInvocation(1, 1);

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(false, attempt, observation),
                "pre-original lifecycle observation accepted");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original lifecycle observation rejected");
    }

    void TestBuildsPlayerPrincipalEventViews()
    {
        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd;
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionStart, kind),
                "session start role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                "session start kind mismatch");
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionStartRejected, kind),
                "session start rejected role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                "session start rejected kind mismatch");
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionEnd, kind),
                "session end role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                "session end kind mismatch");

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated;
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::None, action),
                "none action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::None,
                "none action mismatch");
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::CandidateCreated, action),
                "candidate-created action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                "candidate-created action mismatch");
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::CandidateInvalidated, action),
                "candidate-invalidated action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                "candidate-invalidated action mismatch");

        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "accepted start observation did not build");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event),
                "accepted start event view did not build");
        Require(event.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                "accepted start event kind mismatch");
        Require(event.Action == Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                "accepted start action mismatch");
        Require(event.Bools.data() == boolStorage.data(), "event did not use caller bool storage");
        Require(event.Bools.size() == 2, "accepted start bool count mismatch");
        Require(event.Bools[0].Field == Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin,
                "accepted start first bool field mismatch");
        Require(event.Bools[0].Value, "accepted start bIsFromLogin mismatch");
        Require(event.Bools[1].Field == Obelisk::Core::PlayerPrincipalBoolField::ReturnValue,
                "accepted start second bool field mismatch");
        Require(event.Bools[1].Value, "accepted start ReturnValue mismatch");

        observation.BoolStorage[0].Value = false;
        Require(event.Bools[0].Value, "event view retained copied observation storage");

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "rejected start observation did not build");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "rejected start event view mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "session end observation did not build");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "session end event view mismatch");
    }

    void TestPlayerPrincipalEventViewRejectsMalformedObservations()
    {
        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
        Require(!Observer::TryMapPlayerPrincipalEventKind(
                    static_cast<Observer::LifecycleRole>(99),
                    kind),
                "unknown lifecycle role mapped to event kind");

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::None;
        Require(!Observer::TryMapPlayerPrincipalAction(
                    static_cast<Observer::PrincipalAction>(99),
                    action),
                "unknown principal action mapped to core action");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "valid accepted start observation did not build");

        Observer::CopiedLifecycleObservation malformed = observation;
        malformed.Role = static_cast<Observer::LifecycleRole>(99);
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "unknown lifecycle role built event view");

        malformed = observation;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "accepted start without candidate-created action built event view");

        malformed = observation;
        malformed.BoolCount = 0;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start without canonical bools built event view");

        malformed = observation;
        std::swap(malformed.BoolStorage[0], malformed.BoolStorage[1]);
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with swapped bool fields built event view");

        malformed = observation;
        malformed.Role = Observer::LifecycleRole::SessionStartRejected;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "accepted start bools built rejected event view");

        malformed = observation;
        malformed.BoolStorage[1].Value = false;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "rejected start bools built accepted event view");

        malformed = observation;
        malformed.RedactedCount = 2;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with missing redacted field built event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "valid session end observation did not build");
        malformed = observation;
        malformed.BoolStorage[0] = {
            .Field = LifecycleField::ReturnValue,
            .Value = true,
        };
        malformed.BoolCount = 1;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with bool payload built event view");

        malformed = observation;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end without invalidation action built event view");
    }
}

int main()
{
    TestGateMatrix();
    TestNameAndBudgetPrefilters();
    TestTryIdentifyFastPathsDoNotRead();
    TestBuildsHandleNewPlayerObservation();
    TestBuildsOnLogoutObservationWithoutIdentity();
    TestAfterOriginalGuard();
    TestBuildsPlayerPrincipalEventViews();
    TestPlayerPrincipalEventViewRejectsMalformedObservations();

    std::cout << "ProcessEventPlayerPrincipalLifecycleObserverTests passed\n";
    return 0;
}
