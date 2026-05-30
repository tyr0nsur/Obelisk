#include "hooks/ProcessEventMissionReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventMissionReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kBPAllowPlayerToLeaveMissionNameIndex = 1211;
    constexpr int32_t kBPOnPlayerRemovedFromMissionNameIndex = 1582;
    constexpr int32_t kAddPlayerToMissionNameIndex = 7649;
    constexpr int32_t kMissionTypeNameIndex = 7646;
    constexpr int32_t kGetPlayerUsableItemsNameIndex = 7702;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kArrayPropertyClassNameIndex = 9;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kArrayPropertyClassObjectIndex = 528;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kMissionTypeObjectIndex = 179;
    constexpr int32_t kControllerNameIndex = 5908;
    constexpr int32_t kCharacterNameIndex = 7990;
    constexpr int32_t kPlayerNameIndex = 9972;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kPlayerPawnNameIndex = 21376;
    constexpr int32_t kBForceAddNameIndex = 22956;
    constexpr int32_t kPlayerCharacterNameIndex = 22961;
    constexpr int32_t kBLastPhaseSuccessNameIndex = 22976;
    constexpr int32_t kBFromMissionCompleteEventNameIndex = 22980;
    constexpr int32_t kOutItemIDsNameIndex = 23031;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint64_t kArrayOutPropertyFlags = 0x380;
    constexpr uint8_t kMissionBoolFieldSize = 0x01;
    constexpr uint8_t kMissionBoolByteOffset = 0x00;
    constexpr uint8_t kMissionBoolByteMask = 0x01;
    constexpr uint8_t kMissionBoolFieldMask = 0xff;

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
        int Calls = 0;
    };

    bool RegionReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
        ++reader->Calls;
        const auto* ptr = static_cast<const uint8_t*>(address);
        for (const Region& region : reader->Regions)
        {
            if (ptr < region.Start)
                continue;
            const size_t offset = static_cast<size_t>(ptr - region.Start);
            if (offset <= region.Size && size <= region.Size - offset)
                return true;
        }
        return false;
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("expected mission reflection reader exception");
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    template <typename T, size_t N>
    void WriteAt(std::array<uint8_t, N>& buffer, size_t offset, const T& value)
    {
        Require(offset <= buffer.size() && sizeof(T) <= buffer.size() - offset, "test write out of bounds");
        std::memcpy(buffer.data() + offset, &value, sizeof(T));
    }

    template <size_t N>
    void WriteObject(std::array<uint8_t, N>& buffer,
                     int32_t nameIndex,
                     int32_t internalIndex,
                     const void* klass,
                     const void* outer)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const FNameValue name{nameIndex, 0};

        WriteAt(buffer, 0x00, vtable);
        WriteAt(buffer, 0x08, flags);
        WriteAt(buffer, 0x0c, internalIndex);
        WriteAt(buffer, 0x10, klass);
        WriteAt(buffer, 0x18, name);
        WriteAt(buffer, 0x20, outer);
    }

    template <size_t N>
    void WriteProperty(std::array<uint8_t, N>& buffer,
                       const void* next,
                       const void* owner,
                       const void* klass,
                       int32_t nameIndex,
                       int32_t offset,
                       int32_t elementSize,
                       uint64_t propertyFlags)
    {
        WriteObject(buffer, nameIndex, nameIndex, klass, owner);

        const int32_t arrayDim = 1;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, elementSize);
        WriteAt(buffer, 0x38, propertyFlags);
        WriteAt(buffer, 0x4c, offset);

        if (klass)
        {
            FNameValue className{};
            std::memcpy(&className, static_cast<const uint8_t*>(klass) + 0x18, sizeof(className));
            if (className.ComparisonIndex == kBoolPropertyClassNameIndex && className.Number == 0)
            {
                WriteAt(buffer, 0x70, kMissionBoolFieldSize);
                WriteAt(buffer, 0x71, kMissionBoolByteOffset);
                WriteAt(buffer, 0x72, kMissionBoolByteMask);
                WriteAt(buffer, 0x73, kMissionBoolFieldMask);
            }
        }
    }

    struct FieldDef
    {
        int32_t NameIndex = -1;
        int32_t Offset = -1;
        int32_t ElementSize = 0;
        const void* Class = nullptr;
        uint64_t PropertyFlags = 0;
    };

    struct MissionFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> ArrayPropertyClass{};
        std::array<uint8_t, 0x40> FunctionClass{};
        std::array<uint8_t, 0x40> Outer{};
        std::array<uint8_t, 0x30> Params{};
        ReaderContext Context;

        MemoryReader Reader()
        {
            Context.Regions.clear();
            Context.Regions.push_back({Function.data(), Function.size()});
            Context.Regions.push_back({PropertyA.data(), PropertyA.size()});
            Context.Regions.push_back({PropertyB.data(), PropertyB.size()});
            Context.Regions.push_back({PropertyC.data(), PropertyC.size()});
            Context.Regions.push_back({PropertyD.data(), PropertyD.size()});
            Context.Regions.push_back({ObjectPropertyClass.data(), ObjectPropertyClass.size()});
            Context.Regions.push_back({BoolPropertyClass.data(), BoolPropertyClass.size()});
            Context.Regions.push_back({ArrayPropertyClass.data(), ArrayPropertyClass.size()});
            Context.Regions.push_back({FunctionClass.data(), FunctionClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            Context.Calls = 0;
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    void InitClasses(MissionFixture& fixture)
    {
        WriteObject(fixture.ObjectPropertyClass,
                    kObjectPropertyClassNameIndex,
                    kObjectPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.BoolPropertyClass,
                    kBoolPropertyClassNameIndex,
                    kBoolPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.ArrayPropertyClass,
                    kArrayPropertyClassNameIndex,
                    kArrayPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(MissionFixture& fixture,
                       int32_t functionNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 4>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kMissionTypeNameIndex, kMissionTypeObjectIndex, nullptr, nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());

        std::array<std::array<uint8_t, 0x80>*, 4> properties{
            &fixture.PropertyA,
            &fixture.PropertyB,
            &fixture.PropertyC,
            &fixture.PropertyD,
        };
        for (uint16_t i = 0; i < numParms; ++i)
        {
            const void* next = i + 1 < numParms ? properties[i + 1]->data() : nullptr;
            WriteProperty(*properties[i],
                          next,
                          fixture.Function.data(),
                          fields[i].Class,
                          fields[i].NameIndex,
                          fields[i].Offset,
                          fields[i].ElementSize,
                          fields[i].PropertyFlags);
        }

        WriteAt(fixture.Function, 0x38, numParms > 0 ? fixture.PropertyA.data() : nullptr);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildGetPlayerUsableItems(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kGetPlayerUsableItemsNameIndex,
                      0x04420405,
                      2,
                      0x18,
                      0xffff,
                      {{
                          {kCharacterNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kOutItemIDsNameIndex, 0x08, 0x10, fixture.ArrayPropertyClass.data(), kArrayOutPropertyFlags},
                          {},
                          {},
                      }});
    }

    void BuildAddPlayerToMission(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kAddPlayerToMissionNameIndex,
                      0x04020405,
                      3,
                      0x0a,
                      0x09,
                      {{
                          {kPlayerCharacterNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kBForceAddNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kReturnValueNameIndex, 0x09, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                      }});
    }

    void BuildBPAllowPlayerToLeaveMission(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPAllowPlayerToLeaveMissionNameIndex,
                      0x0c020c00,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kPlayerPawnNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
    }

    void BuildBPOnPlayerRemovedFromMission(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPOnPlayerRemovedFromMissionNameIndex,
                      0x0c020c00,
                      4,
                      0x12,
                      0xffff,
                      {{
                          {kPlayerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kControllerNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBFromMissionCompleteEventNameIndex,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kBLastPhaseSuccessNameIndex,
                           0x11,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                      }});
    }

    Attempt Identify(MissionFixture& fixture, int32_t nameIndex)
    {
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            nameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        return attempt;
    }

    Attempt IdentifyMetadataOnly(MissionFixture& fixture, int32_t nameIndex)
    {
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            nameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            nullptr);
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(!attempt.Invocation.HasParameterRanges, "metadata-only mission invocation exposed ranges");
        return attempt;
    }

    void TestGateEvaluation()
    {
        const char* supportedSha = kSupportedShooterGameServerSha256.data();

        Require(EvaluateGate(nullptr, true, true, true, supportedSha).Status == GateStatus::Disabled,
                "missing enable env should disable mission reflection");
        Require(EvaluateGate("0", true, true, true, supportedSha).Status == GateStatus::Disabled,
                "non-1 enable env should disable mission reflection");
        Require(EvaluateGate("1", false, true, true, supportedSha).Status == GateStatus::MissingObserverDebugProfile,
                "missing observer-debug profile gate was not rejected");
        Require(EvaluateGate("1", true, false, true, supportedSha).Status == GateStatus::MissingObserverDebugWindow,
                "missing observer-debug window marker was not rejected");
        Require(EvaluateGate("1", true, true, false, supportedSha).Status == GateStatus::MissingInstanceMarker,
                "missing mission marker gate was not rejected");
        Require(EvaluateGate("1", true, true, true, nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, true, true, "").Status == GateStatus::MissingBinarySha256,
                "empty binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, true, true, "not-this-binary").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary SHA gate was not rejected");

        Gate gate = EvaluateGate("1", true, true, true, supportedSha);
        Require(gate.Status == GateStatus::Enabled, "supported mission reflection gate did not enable");
        Require(gate.Enabled(), "enabled mission reflection gate did not report enabled");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "enabled gate did not retain binary SHA");
    }

    void TestObservationBudgetAndFilter()
    {
        Require(!ShouldAttemptObservation(0), "zero mission reflection limit should skip observation");
        Require(ShouldAttemptObservation(1), "non-zero mission reflection limit should allow observation");
        Require(ShouldAttemptNameObservation(kGetPlayerUsableItemsNameIndex, 1),
                "GetPlayerUsableItems FName should pass observation filter");
        Require(ShouldAttemptNameObservation(kAddPlayerToMissionNameIndex, 1),
                "AddPlayerToMission FName should pass observation filter");
        Require(ShouldAttemptNameObservation(kBPAllowPlayerToLeaveMissionNameIndex, 1),
                "BPAllowPlayerToLeaveMission FName should pass observation filter");
        Require(ShouldAttemptNameObservation(kBPOnPlayerRemovedFromMissionNameIndex, 1),
                "BPOnPlayerRemovedFromMission FName should pass observation filter");
        Require(!ShouldAttemptNameObservation(42, 1), "non-mission FName should not pass observation filter");
        Require(!ShouldAttemptNameObservation(kAddPlayerToMissionNameIndex, 0),
                "zero budget should skip matching mission FName");
        Require(ShouldAttemptRuntimeObservation(1),
                "single non-zero mission observation/log budget should activate runtime observation");
        Require(!ShouldAttemptRuntimeObservation(0),
                "single zero mission observation/log budget should skip runtime observation");
        Require(ShouldLogObservation(1, 1), "in-budget mission observation should log");
        Require(!ShouldLogObservation(0, 25), "zero mission observation number should not log");
        Require(!ShouldLogObservation(2, 1), "over-budget mission observation should not log");
        Require(!ShouldLogObservation(1, 0), "zero mission observation log limit should disable logs");

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Require(!TryReserveObservationBudget(counter, 0, observationNumber), "zero limit reserved budget");
        Require(observationNumber == 0, "zero limit did not clear observation number");
        Require(TryReserveObservationBudget(counter, 1, observationNumber), "first reservation failed");
        Require(observationNumber == 1, "first observation number mismatch");
        Require(!TryReserveObservationBudget(counter, 1, observationNumber), "budget reservation exceeded limit");
        Require(counter.load() == 1, "budget counter mismatch");

        std::atomic<uint64_t> observationCounter{0};
        Require(!ShouldAttemptRuntimeObservation(observationCounter, 0),
                "zero mission observation/log budget reported active runtime observation");
        Require(ShouldAttemptRuntimeObservation(observationCounter, 1),
                "observation/log budget did not activate mission runtime observation");
        Require(HasObservationBudgetRemaining(observationCounter, 1),
                "fresh mission observation counter did not report remaining budget");

        Require(TryReserveObservationBudget(observationCounter, 1, observationNumber),
                "mission observation/log budget reservation failed");
        Require(observationNumber == 1, "mission observation/log number mismatch");
        Require(observationCounter.load() == 1, "mission observation/log counter mismatch");
        Require(!HasObservationBudgetRemaining(observationCounter, 1),
                "exhausted mission observation/log counter reported remaining budget");
        Require(!ShouldAttemptRuntimeObservation(observationCounter, 1),
                "exhausted mission observation/log budget still activated runtime observation");
    }

    void TestHookLevelZeroObservationLimitDoesNotRead()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);

        std::atomic<uint64_t> observationCounter{0};
        uint64_t observationNumber = 99;
        Attempt attempt = TryObserveInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data(),
            observationCounter,
            0,
            observationNumber);

        Require(attempt.Status == AttemptStatus::BudgetExhausted,
                "zero mission observation/log limit did not stop hook-level observation");
        Require(observationNumber == 0, "zero mission observation/log limit kept an observation number");
        Require(observationCounter.load() == 0, "zero mission observation/log limit changed the counter");
        Require(fixture.Context.Calls == 0,
                "zero mission observation/log limit touched UFunction memory");
    }

    void TestHookLevelObservationBudgetIsReservedBeforeRead()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);
        fixture.Params[0x08] = 1;
        fixture.Params[0x09] = 1;

        std::atomic<uint64_t> observationCounter{0};
        uint64_t observationNumber = 0;
        Attempt attempt = TryObserveInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data(),
            observationCounter,
            1,
            observationNumber);

        Require(attempt.Status == AttemptStatus::Matched,
                "non-zero mission observation/log budget did not observe matching mission call");
        Require(observationNumber == 1, "mission hook-level observation number mismatch");
        Require(observationCounter.load() == 1, "mission hook-level observation counter mismatch");
        Require(fixture.Context.Calls > 0, "mission hook-level observation did not read metadata");

        MissionFixture exhaustedFixture;
        BuildAddPlayerToMission(exhaustedFixture);
        attempt = TryObserveInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            exhaustedFixture.Reader(),
            exhaustedFixture.Function.data(),
            exhaustedFixture.Params.data(),
            observationCounter,
            1,
            observationNumber);

        Require(attempt.Status == AttemptStatus::BudgetExhausted,
                "exhausted mission observation/log budget allowed another hook-level attempt");
        Require(observationNumber == 0, "exhausted mission observation/log budget kept an observation number");
        Require(exhaustedFixture.Context.Calls == 0,
                "exhausted mission observation/log budget touched UFunction memory");
    }

    void TestHookLevelDisabledAndNonMissionDoNotReadOrReserve()
    {
        for (GateStatus status : {
                 GateStatus::Disabled,
                 GateStatus::MissingObserverDebugProfile,
                 GateStatus::MissingObserverDebugWindow,
                 GateStatus::MissingInstanceMarker,
                 GateStatus::MissingBinarySha256,
                 GateStatus::UnsupportedBinarySha256,
             })
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);

            std::atomic<uint64_t> observationCounter{0};
            uint64_t observationNumber = 99;
            Attempt attempt = TryObserveInvocation(
                {status, std::string(kSupportedShooterGameServerSha256)},
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data(),
                observationCounter,
                1,
                observationNumber);

            Require(attempt.Status == AttemptStatus::Disabled,
                    "non-enabled mission gate did not short-circuit hook-level observation");
            Require(observationNumber == 0, "non-enabled mission gate kept an observation number");
            Require(observationCounter.load() == 0, "non-enabled mission gate reserved observation budget");
            Require(fixture.Context.Calls == 0, "non-enabled mission gate touched UFunction memory");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);

            std::atomic<uint64_t> observationCounter{0};
            uint64_t observationNumber = 99;
            Attempt attempt = TryObserveInvocation(
                EnabledGate(),
                42,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data(),
                observationCounter,
                1,
                observationNumber);

            Require(attempt.Status == AttemptStatus::NonMissionFunction,
                    "non-mission name did not short-circuit hook-level observation");
            Require(observationNumber == 0, "non-mission name kept an observation number");
            Require(observationCounter.load() == 0, "non-mission name reserved observation budget");
            Require(fixture.Context.Calls == 0, "non-mission name touched UFunction memory");
        }
    }

    void TestDisabledGatesDoNotRead()
    {
        for (GateStatus status : {
                 GateStatus::Disabled,
                 GateStatus::MissingObserverDebugProfile,
                 GateStatus::MissingObserverDebugWindow,
                 GateStatus::MissingInstanceMarker,
                 GateStatus::MissingBinarySha256,
                 GateStatus::UnsupportedBinarySha256,
             })
        {
            ReaderContext context;
            MemoryReader reader{RegionReader, &context};
            Attempt attempt = TryIdentifyInvocation(
                {status, std::string(kSupportedShooterGameServerSha256)},
                kAddPlayerToMissionNameIndex,
                reader,
                reinterpret_cast<void*>(0x10000),
                reinterpret_cast<void*>(0x20000));

            Require(attempt.Status == AttemptStatus::Disabled, "disabled mission gate did not short-circuit");
            Require(context.Calls == 0, "disabled mission gate touched UFunction memory");
        }
    }

    void TestNonMissionNameDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            42,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::NonMissionFunction,
                "non-mission name did not short-circuit");
        Require(context.Calls == 0, "non-mission name touched UFunction memory");
    }

    void TestIdentifyContainsReaderExceptions()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Rejected,
                "reader exception escaped mission recognition as a non-rejection");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "reader exception did not fail closed as an implausible read");
    }

    void TestAcceptedTargets()
    {
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);
            Require(attempt.Invocation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                    "GetPlayerUsableItems function mismatch");
            Require(fixture.Context.Calls > 0, "accepted GetPlayerUsableItems did not read metadata");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 0;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);
            Require(attempt.Invocation.Function == MissionReflection::MissionFunction::AddPlayerToMission,
                    "AddPlayerToMission function mismatch");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);
            Require(attempt.Invocation.Function == MissionReflection::MissionFunction::BPAllowPlayerToLeaveMission,
                    "BPAllowPlayerToLeaveMission function mismatch");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);
            Require(attempt.Invocation.Function == MissionReflection::MissionFunction::BPOnPlayerRemovedFromMission,
                    "BPOnPlayerRemovedFromMission function mismatch");
        }
    }

    void TestUnknownAndInvalidRejects()
    {
        TestNonMissionNameDoesNotRead();

        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);
        WriteAt(fixture.Function, 0x90, uint32_t{0x0c020c00});

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Rejected, "invalid mission metadata was not rejected");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "invalid mission metadata did not fail as implausible");
        Require(fixture.Context.Calls > 0, "invalid matching mission FName did not inspect metadata");
    }

    void TestHookLevelRejectsWrongBoolTailMetadata()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);
        fixture.Params[0x08] = 1;
        fixture.Params[0x09] = 0;
        WriteAt(fixture.PropertyB, 0x72, uint8_t{0xff});
        WriteAt(fixture.PropertyB, 0x73, uint8_t{0xff});

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kAddPlayerToMissionNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Rejected,
                "mission hook accepted wrong BoolProperty tail metadata");
        Require(attempt.Invocation.Fields.empty(),
                "rejected mission hook attempt left stale fields");

        CopiedMissionObservation observation;
        observation.Function = MissionReflection::MissionFunction::BPOnPlayerRemovedFromMission;
        observation.FunctionNameIndex = 123456;
        observation.OuterNameIndex = 654321;
        observation.BoolStorage[0].Field = MissionReflection::MissionField::BLastPhaseSuccess;
        observation.BoolStorage[0].Value = true;
        observation.BoolStorage[1].Field = MissionReflection::MissionField::BFromMissionCompleteEvent;
        observation.BoolStorage[1].Value = true;
        observation.BoolCount = observation.BoolStorage.size();
        Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                "rejected mission bool-tail attempt produced copied bool output");
        Require(observation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                "rejected mission bool-tail attempt did not clear function");
        Require(observation.FunctionNameIndex == -1,
                "rejected mission bool-tail attempt did not clear function name");
        Require(observation.OuterNameIndex == -1,
                "rejected mission bool-tail attempt did not clear outer name");
        Require(observation.BoolCount == 0,
                "rejected mission bool-tail attempt did not clear bool count");
        Require(!observation.BoolStorage[0].Value && !observation.BoolStorage[1].Value,
                "rejected mission bool-tail attempt did not clear bool storage");
    }

    void TestExactPrefilterMustMatchReflectedFunction()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kGetPlayerUsableItemsNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Rejected,
                "mismatched mission prefilter FName was accepted");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "mismatched mission prefilter FName did not fail as implausible");
        Require(fixture.Context.Calls > 0,
                "mismatched supported mission FName did not inspect metadata");
    }

    void TestCopiedObservationPayloadShape()
    {
        static_assert(std::is_standard_layout<CopiedMissionObservation>::value,
                      "mission observation must remain a plain copied payload");
        static_assert(std::is_trivially_copyable<CopiedMissionObservation>::value,
                      "mission observation must remain trivially copyable");
        static_assert(std::is_standard_layout<MissionBoolObservation>::value,
                      "mission bool observation must remain a plain copied payload");
        static_assert(std::is_trivially_copyable<MissionBoolObservation>::value,
                      "mission bool observation must remain trivially copyable");

        Require(offsetof(CopiedMissionObservation, FunctionNameIndex) ==
                    offsetof(CopiedMissionObservation, Function) +
                        sizeof(MissionReflection::MissionFunction),
                "mission observation grew data before FunctionNameIndex");
        Require(offsetof(CopiedMissionObservation, OuterNameIndex) ==
                    offsetof(CopiedMissionObservation, FunctionNameIndex) + sizeof(int32_t),
                "mission observation grew data before OuterNameIndex");
        Require(offsetof(CopiedMissionObservation, BoolStorage) >=
                    offsetof(CopiedMissionObservation, OuterNameIndex) + sizeof(int32_t),
                "mission observation bool storage overlaps metadata");
        const size_t boolStorageEnd = offsetof(CopiedMissionObservation, BoolStorage) +
                                      sizeof(std::array<MissionBoolObservation, 2>);
        Require(offsetof(CopiedMissionObservation, BoolCount) >= boolStorageEnd &&
                    offsetof(CopiedMissionObservation, BoolCount) <
                        boolStorageEnd + alignof(size_t),
                "mission observation grew data between bool storage and count");
        Require(sizeof(CopiedMissionObservation) ==
                    offsetof(CopiedMissionObservation, BoolCount) + sizeof(size_t),
                "mission observation grew trailing payload fields");
    }

    void TestBuildsMetadataAndCopiedBoolObservationOnly()
    {
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build GetPlayerUsableItems observation");
            Require(observation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                    "GetPlayerUsableItems observation function mismatch");
            Require(observation.FunctionNameIndex == kGetPlayerUsableItemsNameIndex,
                    "GetPlayerUsableItems observation function name mismatch");
            Require(observation.OuterNameIndex == kMissionTypeNameIndex,
                    "GetPlayerUsableItems observation outer mismatch");
            Require(observation.BoolCount == 0, "object/array mission fields were copied");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 0;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);
            const auto beforeBuild = fixture.Params;

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build AddPlayerToMission observation");
            Require(fixture.Params == beforeBuild,
                    "building AddPlayerToMission observation mutated params");
            fixture.Params[0x08] = 0;
            fixture.Params[0x09] = 1;

            Require(observation.Function == MissionReflection::MissionFunction::AddPlayerToMission,
                    "AddPlayerToMission observation function mismatch");
            Require(observation.FunctionNameIndex == kAddPlayerToMissionNameIndex,
                    "AddPlayerToMission observation function name mismatch");
            Require(observation.OuterNameIndex == kMissionTypeNameIndex,
                    "AddPlayerToMission observation outer mismatch");
            Require(observation.BoolCount == 2, "AddPlayerToMission bool count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::BForceAdd,
                    "bForceAdd field mismatch");
            Require(observation.BoolStorage[0].Value, "bForceAdd value was not copied");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::ReturnValue,
                    "return field mismatch");
            Require(!observation.BoolStorage[1].Value, "return value was not copied");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 0;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);
            const auto beforeBuild = fixture.Params;

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build BPOnPlayerRemovedFromMission observation");
            Require(fixture.Params == beforeBuild,
                    "building BPOnPlayerRemovedFromMission observation mutated params");
            Require(observation.BoolCount == 2, "BPOnPlayerRemovedFromMission bool count mismatch");
            Require(observation.BoolStorage[0].Field ==
                        MissionReflection::MissionField::BFromMissionCompleteEvent,
                    "bFromMissionCompleteEvent field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "bFromMissionCompleteEvent value was not copied");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::BLastPhaseSuccess,
                    "bLastPhaseSuccess field mismatch");
            Require(!observation.BoolStorage[1].Value, "bLastPhaseSuccess value was not copied");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);
            const auto beforeBuild = fixture.Params;

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build BPAllowPlayerToLeaveMission observation");
            Require(fixture.Params == beforeBuild,
                    "building BPAllowPlayerToLeaveMission observation mutated params");
            fixture.Params[0x08] = 0;

            Require(observation.Function == MissionReflection::MissionFunction::BPAllowPlayerToLeaveMission,
                    "BPAllowPlayerToLeaveMission observation function mismatch");
            Require(observation.FunctionNameIndex == kBPAllowPlayerToLeaveMissionNameIndex,
                    "BPAllowPlayerToLeaveMission observation function name mismatch");
            Require(observation.OuterNameIndex == kMissionTypeNameIndex,
                    "BPAllowPlayerToLeaveMission observation outer mismatch");
            Require(observation.BoolCount == 1, "BPAllowPlayerToLeaveMission bool count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::ReturnValue,
                    "BPAllowPlayerToLeaveMission return field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "BPAllowPlayerToLeaveMission return value was not copied");
        }
    }

    void TestCopiedObservationRejectsForgedObjectAndArrayRanges()
    {
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);

            attempt.Invocation.Fields[0].Range = {fixture.Params.data(), 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged Character object range was accepted");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);

            attempt.Invocation.Fields[1].Range = {fixture.Params.data() + 0x08, 0x10};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged OutItemIDs array range was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[0].Range = {fixture.Params.data(), 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged PlayerCharacter object range was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            attempt.Invocation.Fields[0].Range = {fixture.Params.data(), 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged PlayerPawn object range was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            attempt.Invocation.Fields[0].Range = {fixture.Params.data(), 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged Player object range was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            attempt.Invocation.Fields[1].Range = {fixture.Params.data() + 0x08, 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged Controller object range was accepted");
        }
    }

    void PoisonObservation(CopiedMissionObservation& observation)
    {
        observation.Function = MissionReflection::MissionFunction::BPOnPlayerRemovedFromMission;
        observation.FunctionNameIndex = 123456;
        observation.OuterNameIndex = 654321;
        observation.BoolStorage[0].Field = MissionReflection::MissionField::BLastPhaseSuccess;
        observation.BoolStorage[0].Value = true;
        observation.BoolStorage[1].Field = MissionReflection::MissionField::BFromMissionCompleteEvent;
        observation.BoolStorage[1].Value = true;
        observation.BoolCount = observation.BoolStorage.size();
    }

    void RequireObservationCleared(const CopiedMissionObservation& observation, const char* message)
    {
        Require(observation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                message);
        Require(observation.FunctionNameIndex == -1, message);
        Require(observation.OuterNameIndex == -1, message);
        Require(observation.BoolCount == 0, message);
        Require(!observation.BoolStorage[0].Value, message);
        Require(!observation.BoolStorage[1].Value, message);
    }

    void TestMatchedAttemptBoolObservationFence()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);

            std::atomic<uint64_t> observationCounter{0};
            uint64_t observationNumber = 99;
            Attempt attempt = TryObserveInvocation(
                EnabledGate(),
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data(),
                observationCounter,
                0,
                observationNumber);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "zero-budget mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "zero-budget mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);

            std::atomic<uint64_t> observationCounter{1};
            uint64_t observationNumber = 99;
            Attempt attempt = TryObserveInvocation(
                EnabledGate(),
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data(),
                observationCounter,
                1,
                observationNumber);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "exhausted-budget mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "exhausted-budget mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);

            Attempt attempt = TryIdentifyInvocation(
                {GateStatus::Disabled, std::string(kSupportedShooterGameServerSha256)},
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "disabled mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "disabled mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                42,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "non-mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "non-mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{0x0c020c00});
            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "rejected mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "rejected mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "GetPlayerUsableItems produced copied bool output");
            RequireObservationCleared(observation,
                                      "GetPlayerUsableItems bool-only attempt did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "metadata-only AddPlayerToMission produced copied bool output");
            RequireObservationCleared(observation,
                                      "metadata-only mission attempt did not clear copied bool output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 0;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "matched AddPlayerToMission attempt did not produce copied bool output");
            Require(observation.BoolCount == 2, "AddPlayerToMission bool-only count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::BForceAdd,
                    "AddPlayerToMission bool-only first field mismatch");
            Require(observation.BoolStorage[0].Value, "AddPlayerToMission bool-only first value mismatch");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::ReturnValue,
                    "AddPlayerToMission bool-only return field mismatch");
            Require(!observation.BoolStorage[1].Value, "AddPlayerToMission bool-only return value mismatch");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "matched BPAllowPlayerToLeaveMission attempt did not produce copied bool output");
            Require(observation.BoolCount == 1, "BPAllowPlayerToLeaveMission bool-only count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::ReturnValue,
                    "BPAllowPlayerToLeaveMission bool-only return field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "BPAllowPlayerToLeaveMission bool-only return value mismatch");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 0;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationForMatchedAttempt(attempt, observation),
                    "matched BPOnPlayerRemovedFromMission attempt did not produce copied bool output");
            Require(observation.BoolCount == 2, "BPOnPlayerRemovedFromMission bool-only count mismatch");
            Require(observation.BoolStorage[0].Field ==
                        MissionReflection::MissionField::BFromMissionCompleteEvent,
                    "BPOnPlayerRemovedFromMission bool-only first field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "BPOnPlayerRemovedFromMission bool-only first value mismatch");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::BLastPhaseSuccess,
                    "BPOnPlayerRemovedFromMission bool-only second field mismatch");
            Require(!observation.BoolStorage[1].Value,
                    "BPOnPlayerRemovedFromMission bool-only second value mismatch");
        }
    }

    void TestPostOriginalBoolObservationHelper()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 0;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationAfterOriginal(true, attempt, observation),
                    "post-original AddPlayerToMission attempt did not produce copied bool output");
            Require(observation.BoolCount == 2, "post-original AddPlayerToMission bool count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::BForceAdd,
                    "post-original AddPlayerToMission first bool field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "post-original AddPlayerToMission first bool value mismatch");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::ReturnValue,
                    "post-original AddPlayerToMission return field mismatch");
            Require(!observation.BoolStorage[1].Value,
                    "post-original AddPlayerToMission return value mismatch");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationAfterOriginal(false, attempt, observation),
                    "pre-original AddPlayerToMission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "pre-original AddPlayerToMission attempt did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{0x0c020c00});
            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationAfterOriginal(true, attempt, observation),
                    "post-original rejected mission attempt produced copied bool output");
            RequireObservationCleared(observation,
                                      "post-original rejected mission attempt did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationAfterOriginal(true, attempt, observation),
                    "post-original BPAllowPlayerToLeaveMission attempt did not produce copied bool output");
            fixture.Params[0x08] = 0;
            Require(observation.BoolCount == 1,
                    "post-original BPAllowPlayerToLeaveMission bool count mismatch");
            Require(observation.BoolStorage[0].Field == MissionReflection::MissionField::ReturnValue,
                    "post-original BPAllowPlayerToLeaveMission return field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "post-original BPAllowPlayerToLeaveMission copied data was not independent");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 0;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionBoolObservationAfterOriginal(true, attempt, observation),
                    "post-original BPOnPlayerRemovedFromMission attempt did not produce copied bool output");
            fixture.Params[0x10] = 0;
            fixture.Params[0x11] = 1;
            Require(observation.BoolCount == 2,
                    "post-original BPOnPlayerRemovedFromMission bool count mismatch");
            Require(observation.BoolStorage[0].Field ==
                        MissionReflection::MissionField::BFromMissionCompleteEvent,
                    "post-original BPOnPlayerRemovedFromMission first bool field mismatch");
            Require(observation.BoolStorage[0].Value,
                    "post-original BPOnPlayerRemovedFromMission first bool was not copied");
            Require(observation.BoolStorage[1].Field == MissionReflection::MissionField::BLastPhaseSuccess,
                    "post-original BPOnPlayerRemovedFromMission second bool field mismatch");
            Require(!observation.BoolStorage[1].Value,
                    "post-original BPOnPlayerRemovedFromMission copied data was not independent");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = Identify(fixture, kGetPlayerUsableItemsNameIndex);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionBoolObservationAfterOriginal(true, attempt, observation),
                    "post-original GetPlayerUsableItems produced copied bool output");
            RequireObservationCleared(observation,
                                      "post-original GetPlayerUsableItems did not clear copied output");
        }
    }

    void TestCopiedObservationRejectsWrongFieldShape()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            std::swap(attempt.Invocation.Fields[1], attempt.Invocation.Fields[2]);

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "wrong copied mission field order was accepted");
            RequireObservationCleared(observation,
                                      "wrong copied mission field order did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].PropertyNameIndex = kReturnValueNameIndex;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "wrong copied mission field name was accepted");
            RequireObservationCleared(observation,
                                      "wrong copied mission field name did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Offset = 0x09;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "wrong copied mission field offset was accepted");
            RequireObservationCleared(observation,
                                      "wrong copied mission field offset did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Size = 0x02;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "wrong copied mission field size was accepted");
            RequireObservationCleared(observation,
                                      "wrong copied mission field size did not clear copied output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].ExposesRange = false;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "wrong copied mission range exposure was accepted");
            RequireObservationCleared(observation,
                                      "wrong copied mission range exposure did not clear copied output");
        }
    }

    void TestCopiedObservationRejectsInvalidBoolRangesAndCounts()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Range.Data = nullptr;
            attempt.Invocation.Fields[1].Range.Size = 1;

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "copied mission bool null data with one-byte range was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Range.Size = 2;

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "copied mission bool range size larger than one byte was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            attempt.Invocation.Fields[1].Range.Size = 0;

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "copied mission bool range size below one byte was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Range = {fixture.PropertyA.data(), 1};

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged copied mission bool range outside params was accepted");
            RequireObservationCleared(observation,
                                      "forged copied mission bool range outside params did not clear output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[1].Range = {fixture.Params.data() + 0x09, 1};

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged copied mission bool range with wrong offset was accepted");
            RequireObservationCleared(observation,
                                      "forged copied mission bool range with wrong offset did not clear output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.ParameterData = nullptr;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "copied mission bool range without params provenance was accepted");
            RequireObservationCleared(observation,
                                      "copied mission bool range without params provenance did not clear output");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            attempt.Invocation.Fields[2].Range = {};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "copied mission bool count below expected was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 2;
            fixture.Params[0x09] = 1;

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kAddPlayerToMissionNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            Require(attempt.Status == AttemptStatus::Rejected,
                    "non-canonical mission bool byte reached copied observation builder");
            Require(attempt.Invocation.Fields.empty(),
                    "rejected non-canonical mission attempt left copied field ranges");
        }
    }

    void TestCopiedObservationRejectsForgedNonCanonicalBoolRanges()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            fixture.Params[0x08] = 2;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged non-canonical AddPlayerToMission bool range was accepted");
            RequireObservationCleared(observation,
                                      "forged non-canonical AddPlayerToMission range did not clear output");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            fixture.Params[0x08] = 2;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged non-canonical BPAllowPlayerToLeaveMission bool range was accepted");
            RequireObservationCleared(observation,
                                      "forged non-canonical BPAllowPlayerToLeaveMission range did not clear output");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            fixture.Params[0x11] = 2;

            CopiedMissionObservation observation;
            PoisonObservation(observation);
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "forged non-canonical BPOnPlayerRemovedFromMission bool range was accepted");
            RequireObservationCleared(observation,
                                      "forged non-canonical BPOnPlayerRemovedFromMission range did not clear output");
        }
    }

    void TestCopiedObservationApprovedBoolSurface()
    {
        std::array<MissionReflection::MissionField, 5> observed{};
        size_t observedCount = 0;

        auto appendObserved = [&](const CopiedMissionObservation& observation) {
            for (size_t i = 0; i < observation.BoolCount; ++i)
                observed[observedCount++] = observation.BoolStorage[i].Field;
        };

        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;
            Attempt attempt = Identify(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build AddPlayerToMission approved bool observation");
            appendObserved(observation);
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;
            Attempt attempt = Identify(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build BPAllowPlayerToLeaveMission approved bool observation");
            appendObserved(observation);
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;
            Attempt attempt = Identify(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "failed to build BPOnPlayerRemovedFromMission approved bool observation");
            appendObserved(observation);
        }

        Require(observedCount == observed.size(), "mission copied bool surface count changed");
        Require(observed[0] == MissionReflection::MissionField::BForceAdd,
                "mission copied bool surface lost bForceAdd");
        Require(observed[1] == MissionReflection::MissionField::ReturnValue,
                "mission copied bool surface lost AddPlayerToMission return");
        Require(observed[2] == MissionReflection::MissionField::ReturnValue,
                "mission copied bool surface lost BPAllowPlayerToLeaveMission return");
        Require(observed[3] == MissionReflection::MissionField::BFromMissionCompleteEvent,
                "mission copied bool surface lost bFromMissionCompleteEvent");
        Require(observed[4] == MissionReflection::MissionField::BLastPhaseSuccess,
                "mission copied bool surface lost bLastPhaseSuccess");
    }

    void TestCopiedObservationRequiresParameterRangesForCopiedTargets()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kAddPlayerToMissionNameIndex);

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "metadata-only AddPlayerToMission copied target was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kBPAllowPlayerToLeaveMissionNameIndex);

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "metadata-only BPAllowPlayerToLeaveMission copied target was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kBPOnPlayerRemovedFromMissionNameIndex);

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "metadata-only BPOnPlayerRemovedFromMission copied target was accepted");
        }
    }

    void TestMetadataOnlyObservationIsLimitedToGetPlayerUsableItems()
    {
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kGetPlayerUsableItemsNameIndex);

            CopiedMissionObservation observation;
            Require(TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "metadata-only GetPlayerUsableItems was rejected");
            Require(observation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                    "metadata-only GetPlayerUsableItems function mismatch");
            Require(observation.BoolCount == 0,
                    "metadata-only GetPlayerUsableItems copied bool values");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            Attempt attempt = IdentifyMetadataOnly(fixture, kGetPlayerUsableItemsNameIndex);

            attempt.Invocation.Fields[0].Range = {fixture.Params.data(), 0x08};

            CopiedMissionObservation observation;
            Require(!TryBuildCopiedMissionObservation(attempt.Invocation, observation),
                    "metadata-only GetPlayerUsableItems accepted a forged object range");
        }
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationBudgetAndFilter();
    TestHookLevelZeroObservationLimitDoesNotRead();
    TestHookLevelObservationBudgetIsReservedBeforeRead();
    TestHookLevelDisabledAndNonMissionDoNotReadOrReserve();
    TestDisabledGatesDoNotRead();
    TestNonMissionNameDoesNotRead();
    TestIdentifyContainsReaderExceptions();
    TestAcceptedTargets();
    TestUnknownAndInvalidRejects();
    TestHookLevelRejectsWrongBoolTailMetadata();
    TestExactPrefilterMustMatchReflectedFunction();
    TestCopiedObservationPayloadShape();
    TestBuildsMetadataAndCopiedBoolObservationOnly();
    TestCopiedObservationRejectsForgedObjectAndArrayRanges();
    TestMatchedAttemptBoolObservationFence();
    TestPostOriginalBoolObservationHelper();
    TestCopiedObservationRejectsWrongFieldShape();
    TestCopiedObservationRejectsInvalidBoolRangesAndCounts();
    TestCopiedObservationRejectsForgedNonCanonicalBoolRanges();
    TestCopiedObservationApprovedBoolSurface();
    TestCopiedObservationRequiresParameterRangesForCopiedTargets();
    TestMetadataOnlyObservationIsLimitedToGetPlayerUsableItems();

    std::cout << "ProcessEventMissionReflectionTests passed\n";
    return 0;
}
