#include "hooks/ProcessEventDispatch.h"
#include "hooks/ProcessEventStructureReflection.h"
#include "core/EventManager.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

namespace
{
    using namespace Obelisk::Hooks::ProcessEventStructureReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kVerifyPinCodeNameIndex = 7636;
    constexpr int32_t kAllowStructureAccessNameIndex = 7541;
    constexpr int32_t kIsAllowedToDemolishNameIndex = 7574;
    constexpr int32_t kSetVariantNameIndex = 7605;
    constexpr int32_t kAllowToggleActivationNameIndex = 7620;
    constexpr int32_t kCanSeatNameIndex = 8481;
    constexpr int32_t kPrimalStructureNameIndex = 7539;
    constexpr int32_t kPrimalStructureItemContainerNameIndex = 7617;
    constexpr int32_t kPrimalStructureSeatingNameIndex = 8480;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kForPCNameIndex = 18805;
    constexpr int32_t kForCharacterNameIndex = 17726;
    constexpr int32_t kBForceNameIndex = 18793;
    constexpr int32_t kPinCodeNameIndex = 22699;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kVariantIndexNameIndex = 22292;
    constexpr int32_t kBForceSetNameIndex = 22388;

    int g_BlockingPreCallbackCount = 0;
    int g_OriginalProcessEventCallCount = 0;

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

    struct FieldDef
    {
        int32_t NameIndex = -1;
        int32_t Offset = -1;
        int32_t ElementSize = 0;
        const void* Class = nullptr;
    };

    struct CapturedStructureEvent
    {
        Obelisk::Core::StructureEventKind Kind = Obelisk::Core::StructureEventKind::VerifyPinCode;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::vector<Obelisk::Core::StructureScalarValue> Scalars;
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
        throw std::runtime_error("expected structure reflection reader exception");
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    fs::path MakeTempRoot()
    {
        char templatePath[] = "/tmp/obelisk_process_event_structure_reflection_tests.XXXXXX";
        char* directory = mkdtemp(templatePath);
        Require(directory != nullptr, "mkdtemp failed");
        return fs::path(directory);
    }

    void EnableProcessEventBlockingGate(const fs::path& root)
    {
        setenv("OBELISK_ROOT", root.string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
        setenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-process-event-blocking");
        Require(marker.is_open(), "failed to create ProcessEvent blocking marker");
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(true);
    }

    void DisableProcessEventBlockingGate()
    {
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(false);
        unsetenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING");
        unsetenv("OBELISK_INSTANCE_ID");
        unsetenv("OBELISK_ROOT");
    }

    bool BlockingPreCallback(void*, void*, void*)
    {
        ++g_BlockingPreCallbackCount;
        return false;
    }

    void CountOriginalProcessEventCall(void*, void*, void*)
    {
        ++g_OriginalProcessEventCallCount;
    }

    void CaptureStructureEvent(const Obelisk::Core::StructureEventView& event, void* userData)
    {
        auto* captured = static_cast<std::vector<CapturedStructureEvent>*>(userData);
        captured->push_back({
            event.Kind,
            event.FunctionNameIndex,
            event.OuterNameIndex,
            std::vector<Obelisk::Core::StructureScalarValue>(event.Scalars.begin(), event.Scalars.end()),
        });
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
                       int32_t elementSize)
    {
        WriteObject(buffer, nameIndex, nameIndex, klass, owner);

        const int32_t arrayDim = 1;
        const uint64_t propertyFlags = 0x80;
        WriteAt(buffer, 0x28, next);
        WriteAt(buffer, 0x30, arrayDim);
        WriteAt(buffer, 0x34, elementSize);
        WriteAt(buffer, 0x38, propertyFlags);
        WriteAt(buffer, 0x4c, offset);
    }

    struct StructureFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> IntPropertyClass{};
        std::array<uint8_t, 0x40> Outer{};
        std::array<uint8_t, 0x20> Params{};
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
            Context.Regions.push_back({IntPropertyClass.data(), IntPropertyClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    void InitClasses(StructureFixture& fixture)
    {
        WriteObject(fixture.ObjectPropertyClass,
                    kObjectPropertyClassNameIndex,
                    kObjectPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.BoolPropertyClass,
                    kBoolPropertyClassNameIndex,
                    kBoolPropertyClassNameIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.IntPropertyClass,
                    kIntPropertyClassNameIndex,
                    kIntPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
    }

    void BuildFunction(StructureFixture& fixture,
                       int32_t functionNameIndex,
                       int32_t outerNameIndex,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 4>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer,
                    outerNameIndex,
                    outerNameIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    reinterpret_cast<const void*>(0x20000),
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
                          fields[i].ElementSize);
        }

        const void* children = fixture.PropertyA.data();
        const uint32_t functionFlags = 0x204000;
        WriteAt(fixture.Function, 0x38, children);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    std::array<FieldDef, 4> ForPCReturnFields(StructureFixture& fixture)
    {
        return {{
            {kForPCNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
            {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
            {},
            {},
        }};
    }

    void BuildVerifyPinCode(StructureFixture& fixture)
    {
        BuildFunction(fixture,
                      kVerifyPinCodeNameIndex,
                      kPrimalStructureItemContainerNameIndex,
                      2,
                      0x05,
                      0x04,
                      {{
                          {kPinCodeNameIndex, 0x00, 0x04, fixture.IntPropertyClass.data()},
                          {kReturnValueNameIndex, 0x04, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                          {},
                      }});
    }

    void BuildSetVariant(StructureFixture& fixture)
    {
        BuildFunction(fixture,
                      kSetVariantNameIndex,
                      kPrimalStructureNameIndex,
                      3,
                      0x06,
                      0x05,
                      {{
                          {kVariantIndexNameIndex, 0x00, 0x04, fixture.IntPropertyClass.data()},
                          {kBForceSetNameIndex, 0x04, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x05, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                      }});
    }

    void BuildCanSeat(StructureFixture& fixture)
    {
        BuildFunction(fixture,
                      kCanSeatNameIndex,
                      kPrimalStructureSeatingNameIndex,
                      4,
                      0x12,
                      0x11,
                      {{
                          {kForPCNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kForCharacterNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data()},
                          {kBForceNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x11, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void TestGateEvaluation()
    {
        const char* supportedSha = kSupportedShooterGameServerSha256.data();

        Require(EvaluateGate(nullptr, true, true, true, supportedSha).Status == GateStatus::Disabled,
                "missing enable env should disable structure reflection");
        Require(EvaluateGate("0", true, true, true, supportedSha).Status == GateStatus::Disabled,
                "non-1 enable env should disable structure reflection");
        Require(EvaluateGate("1", false, true, true, supportedSha).Status == GateStatus::MissingObserverDebugProfile,
                "missing observer-debug profile gate was not rejected");
        Require(EvaluateGate("1", true, false, true, supportedSha).Status == GateStatus::MissingObserverDebugWindow,
                "missing observer-debug window marker was not rejected");
        Require(EvaluateGate("1", true, true, false, supportedSha).Status == GateStatus::MissingInstanceMarker,
                "missing instance marker gate was not rejected");
        Require(EvaluateGate("1", true, true, true, nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, true, true, "").Status == GateStatus::MissingBinarySha256,
                "empty binary SHA gate was not rejected");
        Require(EvaluateGate("1", true, true, true, "not-this-binary").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary SHA gate was not rejected");

        Gate gate = EvaluateGate("1", true, true, true, supportedSha);
        Require(gate.Status == GateStatus::Enabled, "supported structure reflection gate did not enable");
        Require(gate.Enabled(), "enabled structure reflection gate did not report enabled");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "enabled gate did not retain binary SHA");
    }

    void TestObservationLogLimit()
    {
        Require(!ShouldAttemptObservation(0), "zero structure reflection log limit should skip observation");
        Require(ShouldAttemptObservation(1), "non-zero structure reflection log limit should allow observation");
        Require(!ShouldAttemptRuntimeObservation(0, 0),
                "zero log and dispatch limits should skip runtime observation");
        Require(ShouldAttemptRuntimeObservation(1, 0),
                "non-zero log limit should allow runtime observation");
        Require(ShouldAttemptRuntimeObservation(0, 1),
                "non-zero dispatch limit should allow runtime observation");
        Require(!ShouldAttemptNameObservation(kSetVariantNameIndex, 0),
                "zero limit should skip exact structure FName observation");
        Require(ShouldAttemptNameObservation(kSetVariantNameIndex, 1),
                "exact non-pin structure FName should pass observation filter with non-zero limit");
        Require(ShouldAttemptNameObservation(kVerifyPinCodeNameIndex, 1),
                "VerifyPinCode should still pass the general structure observation filter");
        Require(!ShouldAttemptNameObservation(42, 1),
                "non-structure FName should not pass observation filter");
        Require(ShouldAttemptNameObservation(kSetVariantNameIndex, 0, 1),
                "dispatch-only non-pin structure FName should pass observation filter");
        Require(ShouldAttemptNameObservation(kVerifyPinCodeNameIndex, 0, 1),
                "dispatch-only VerifyPinCode FName should still pass the general observation filter");
        Require(!ShouldAttemptNameObservation(42, 0, 1),
                "dispatch-only non-structure FName should not pass observation filter");
        Require(!ShouldLogObservation(0, 25), "zero observation number should not log");
        Require(!ShouldLogObservation(1, 0), "zero structure reflection log limit should disable logs");
        Require(ShouldLogObservation(1, 1), "first observation should log at limit one");
        Require(!ShouldLogObservation(2, 1), "observation beyond limit should not log");

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Require(!HasObservationBudgetRemaining(counter, 0), "zero limit reported remaining budget");
        Require(HasObservationBudgetRemaining(counter, 2), "fresh counter did not report remaining budget");
        Require(!TryReserveObservationBudget(counter, 0, observationNumber),
                "zero limit reserved observation budget");
        Require(observationNumber == 0, "zero limit did not clear observation number");
        Require(TryReserveObservationBudget(counter, 2, observationNumber),
                "first observation budget reservation failed");
        Require(observationNumber == 1, "first observation number mismatch");
        Require(HasObservationBudgetRemaining(counter, 2), "one of two reservations exhausted budget");
        Require(TryReserveObservationBudget(counter, 2, observationNumber),
                "second observation budget reservation failed");
        Require(observationNumber == 2, "second observation number mismatch");
        Require(!HasObservationBudgetRemaining(counter, 2), "exhausted counter reported remaining budget");
        Require(!TryReserveObservationBudget(counter, 2, observationNumber),
                "exhausted limit reserved observation budget");
        Require(observationNumber == 0, "exhausted budget did not clear observation number");

        std::atomic<uint64_t> dispatchCounter{0};
        std::atomic<uint64_t> logCounter{0};
        Require(!ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 0),
                "zero atomic log and dispatch budgets reported active structure observation");
        Require(ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 1),
                "atomic dispatch budget did not activate structure observation");
        Require(!ShouldAttemptDispatchObservation(dispatchCounter, 1, 0),
                "structure dispatch observation activated without subscribers");
        Require(ShouldAttemptDispatchObservation(dispatchCounter, 1, 1),
                "structure dispatch observation did not activate with subscribers");

        Attempt rejectedAttempt;
        rejectedAttempt.Status = AttemptStatus::Rejected;
        observationNumber = 99;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(rejectedAttempt, dispatchCounter, 1, observationNumber),
                "rejected structure attempt consumed dispatch budget");
        Require(observationNumber == 0, "rejected dispatch attempt did not clear observation number");
        Require(dispatchCounter.load() == 0, "rejected structure attempt changed dispatch counter");

        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 7;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 1;
        Attempt matchedAttempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(matchedAttempt.Status == AttemptStatus::Matched, matchedAttempt.Result.Reason.c_str());
        Require(TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "matched structure attempt did not reserve dispatch budget");
        Require(observationNumber == 1, "matched dispatch observation number mismatch");
        Require(dispatchCounter.load() == 1, "matched structure attempt did not advance dispatch counter");
        Require(!TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "exhausted matched dispatch budget reserved again");
        Require(observationNumber == 0, "exhausted matched dispatch budget did not clear observation number");
        Require(!ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 1),
                "exhausted atomic dispatch budget still activated structure observation");
        Require(!ShouldAttemptDispatchObservation(dispatchCounter, 1, 1),
                "exhausted structure dispatch observation reported active with subscribers");
    }

    void TestReflectedStructureNameFilter()
    {
        Require(!IsNonPinCopiedScalarStructureNameIndex(7541),
                "AllowStructureAccess FName was accepted by non-pin filter");
        Require(!IsNonPinCopiedScalarStructureNameIndex(7574),
                "IsAllowedToDemolish FName was accepted by non-pin filter");
        Require(IsNonPinCopiedScalarStructureNameIndex(7605), "SetVariant FName was not accepted");
        Require(IsNonPinCopiedScalarStructureNameIndex(7620), "AllowToggleActivation FName was not accepted");
        Require(!IsNonPinCopiedScalarStructureNameIndex(7636),
                "VerifyPinCode FName was accepted by non-pin filter");
        Require(IsNonPinCopiedScalarStructureNameIndex(8481), "CanSeat FName was not accepted");
        Require(!IsNonPinCopiedScalarStructureNameIndex(42), "unrelated FName was accepted");

        Require(IsReflectedStructureNameIndex(7541), "AllowStructureAccess FName was not accepted");
        Require(IsReflectedStructureNameIndex(7574), "IsAllowedToDemolish FName was not accepted");
        Require(IsReflectedStructureNameIndex(7605), "SetVariant FName was not accepted");
        Require(IsReflectedStructureNameIndex(7620), "AllowToggleActivation FName was not accepted");
        Require(IsReflectedStructureNameIndex(7636), "VerifyPinCode FName was not accepted");
        Require(IsReflectedStructureNameIndex(8481), "CanSeat FName was not accepted");
        Require(!IsReflectedStructureNameIndex(42), "unrelated FName was accepted");
    }

    void TestDisabledGateDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            {},
            kVerifyPinCodeNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Disabled, "disabled gate did not short-circuit");
        Require(context.Calls == 0, "disabled gate touched UFunction memory");
    }

    void TestNonStructureNameDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            42,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::NonStructureFunction, "non-structure name did not short-circuit");
        Require(context.Calls == 0, "non-structure name touched UFunction memory");
    }

    void TestIdentifyContainsReaderExceptions()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Rejected,
                "reader exception escaped structure recognition as a non-rejection");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "reader exception did not fail closed as an implausible read");
    }

    void TestRejectsPrefilterFunctionNameMismatch()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 7;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanSeatNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Rejected,
                "structure prefilter/reflected FunctionName mismatch was accepted");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "structure prefilter/reflected FunctionName mismatch did not fail closed");
        Require(attempt.Invocation.Fields.empty(),
                "structure prefilter/reflected FunctionName mismatch retained invocation fields");
    }

    void TestGeneralIdentifyStillRecognizesVerifyPinCode()
    {
        StructureFixture fixture;
        BuildVerifyPinCode(fixture);
        fixture.Params[4] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kVerifyPinCodeNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched,
                "VerifyPinCode was rejected by general ProcessEvent structure path");
        Require(attempt.Invocation.Function == StructureReflection::StructureFunction::VerifyPinCode,
                "VerifyPinCode function mismatch");
    }

    void RequireScalarRange(const StructureReflection::StructureFieldRange& field,
                            const uint8_t* expectedData,
                            size_t expectedSize,
                            const char* message)
    {
        Require(field.ExposesRange, message);
        Require(field.Range.Data == expectedData, message);
        Require(field.Range.Size == expectedSize, message);
    }

    void RequireObjectRangeHidden(const StructureReflection::StructureFieldRange& field, const char* message)
    {
        Require(!field.ExposesRange, message);
        Require(field.Range.Data == nullptr, message);
    }

    void TestIdentifiesAllStructureHookTargets()
    {
        {
            StructureFixture fixture;
            BuildFunction(fixture, kAllowToggleActivationNameIndex, kPrimalStructureItemContainerNameIndex,
                          2, 0x09, 0x08, ForPCReturnFields(fixture));

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kAllowToggleActivationNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
            Require(attempt.Invocation.Function == StructureReflection::StructureFunction::AllowToggleActivation,
                    "AllowToggleActivation target mismatch");
            Require(attempt.Invocation.Fields.size() == 2, "AllowToggleActivation field count mismatch");
            RequireObjectRangeHidden(attempt.Invocation.Fields[0], "ForPC object range was exposed");
            RequireScalarRange(attempt.Invocation.Fields[1], fixture.Params.data() + 0x08, 1,
                               "return value range mismatch");
        }

        {
            StructureFixture fixture;
            BuildSetVariant(fixture);

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kSetVariantNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
            Require(attempt.Invocation.Function == StructureReflection::StructureFunction::SetVariant,
                    "SetVariant target mismatch");
            Require(attempt.Invocation.Fields.size() == 3, "SetVariant field count mismatch");
            RequireScalarRange(attempt.Invocation.Fields[0], fixture.Params.data(), 4,
                               "VariantIndex range mismatch");
            RequireScalarRange(attempt.Invocation.Fields[1], fixture.Params.data() + 0x04, 1,
                               "bForceSet range mismatch");
            RequireScalarRange(attempt.Invocation.Fields[2], fixture.Params.data() + 0x05, 1,
                               "SetVariant return range mismatch");
        }

        {
            StructureFixture fixture;
            BuildCanSeat(fixture);

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kCanSeatNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
            Require(attempt.Invocation.Function == StructureReflection::StructureFunction::CanSeat,
                    "CanSeat target mismatch");
            Require(attempt.Invocation.Fields.size() == 4, "CanSeat field count mismatch");
            RequireObjectRangeHidden(attempt.Invocation.Fields[0], "CanSeat ForPC range was exposed");
            RequireObjectRangeHidden(attempt.Invocation.Fields[1], "CanSeat ForCharacter range was exposed");
            RequireScalarRange(attempt.Invocation.Fields[2], fixture.Params.data() + 0x10, 1,
                               "CanSeat bForce range mismatch");
            RequireScalarRange(attempt.Invocation.Fields[3], fixture.Params.data() + 0x11, 1,
                               "CanSeat return range mismatch");
        }
    }

    void TestNonPinExcludedTargetsDoNotReserveDispatchBudget()
    {
        for (const int32_t nameIndex : {
                 kVerifyPinCodeNameIndex,
                 kAllowStructureAccessNameIndex,
                 kIsAllowedToDemolishNameIndex,
             })
        {
            StructureFixture fixture;
            if (nameIndex == kVerifyPinCodeNameIndex)
            {
                BuildVerifyPinCode(fixture);
            }
            else
            {
                BuildFunction(fixture,
                              nameIndex,
                              kPrimalStructureNameIndex,
                              2,
                              0x09,
                              0x08,
                              ForPCReturnFields(fixture));
            }

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                nameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());

            Require(attempt.Status == AttemptStatus::Matched,
                    "general structure path rejected a supported target");

            std::atomic<uint64_t> dispatchCounter{0};
            uint64_t observationNumber = 99;
            CopiedStructureEvent event;
            Require(!TryBuildAndReserveDispatchBudgetForNonPinMatchedAttempt(
                        attempt, dispatchCounter, 1, observationNumber, event),
                    "non-pin excluded structure target consumed dispatch budget");
            Require(observationNumber == 0,
                    "non-pin excluded structure target did not clear dispatch observation number");
            Require(dispatchCounter.load() == 0,
                    "non-pin excluded structure target changed dispatch counter");
        }
    }

    void TestRejectsStructureHookWrongOuter()
    {
        StructureFixture fixture;
        BuildFunction(fixture,
                      kSetVariantNameIndex,
                      kPrimalStructureItemContainerNameIndex,
                      3,
                      0x06,
                      0x05,
                      {{
                          {kVariantIndexNameIndex, 0x00, 0x04, fixture.IntPropertyClass.data()},
                          {kBForceSetNameIndex, 0x04, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x05, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                      }});

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Rejected, "wrong structure outer was accepted");
    }

    void TestRejectsPinCodeCopiedStructureEventWithoutDispatchBudget()
    {
        StructureFixture fixture;
        BuildVerifyPinCode(fixture);
        fixture.Params[0] = 1;
        fixture.Params[1] = 2;
        fixture.Params[2] = 3;
        fixture.Params[3] = 4;
        fixture.Params[4] = 1;

        StructureReflection::StructureInvocation invocation;
        ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
            fixture.Reader(),
            MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == StructureReflection::StructureFunction::VerifyPinCode,
                "baseline VerifyPinCode recognizer did not match");

        CopiedStructureEvent event;
        Require(!TryBuildNonPinCopiedStructureEvent(invocation, event),
                "copied non-pin path accepted VerifyPinCode");
        Require(event.View.Scalars.empty(), "failed VerifyPinCode copy left copied scalar span");

        Attempt matchedAttempt;
        matchedAttempt.Status = AttemptStatus::Matched;
        matchedAttempt.Result = ReadResult::Ok();
        matchedAttempt.Invocation = invocation;

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        Require(!TryBuildAndReserveDispatchBudgetForNonPinMatchedAttempt(
                    matchedAttempt, dispatchCounter, 1, observationNumber, event),
                "VerifyPinCode consumed non-pin structure dispatch budget");
        Require(observationNumber == 0, "VerifyPinCode did not clear dispatch observation number");
        Require(dispatchCounter.load() == 0, "VerifyPinCode changed dispatch counter");
    }

    void TestBuildsCopiedStructureEventForScalarStructureTargets()
    {
        {
            StructureFixture fixture;
            BuildSetVariant(fixture);
            const int32_t variant = 11;
            WriteAt(fixture.Params, 0x00, variant);
            fixture.Params[0x04] = 1;
            fixture.Params[0x05] = 0;

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kSetVariantNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());
            Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

            CopiedStructureEvent event;
            Require(TryBuildCopiedStructureEvent(attempt.Invocation, event),
                    "failed to build copied SetVariant event");
            Require(event.View.Kind == Obelisk::Core::StructureEventKind::SetVariant,
                    "SetVariant event kind mismatch");
            Require(event.View.Scalars.size() == 3, "SetVariant scalar count mismatch");
            Require(event.View.Scalars[0].Field == Obelisk::Core::StructureScalarField::VariantIndex,
                    "SetVariant variant field mismatch");
            Require(event.View.Scalars[0].Type == Obelisk::Core::StructureScalarType::Int32,
                    "SetVariant variant type mismatch");
            Require(event.View.Scalars[0].Int32Value == 11, "SetVariant variant value mismatch");
            Require(event.View.Scalars[1].Field == Obelisk::Core::StructureScalarField::BForceSet,
                    "SetVariant bForceSet field mismatch");
            Require(event.View.Scalars[1].BoolValue, "SetVariant bForceSet value mismatch");
            Require(event.View.Scalars[2].Field == Obelisk::Core::StructureScalarField::ReturnValue,
                    "SetVariant return field mismatch");
            Require(!event.View.Scalars[2].BoolValue, "SetVariant return value mismatch");
        }
        {
            StructureFixture fixture;
            BuildCanSeat(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;

            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                kCanSeatNameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data());
            Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

            CopiedStructureEvent event;
            Require(TryBuildCopiedStructureEvent(attempt.Invocation, event),
                    "failed to build copied CanSeat event");
            Require(event.View.Kind == Obelisk::Core::StructureEventKind::CanSeat,
                    "CanSeat event kind mismatch");
            Require(event.View.Scalars.size() == 2, "CanSeat copied object parameters");
            Require(event.View.Scalars[0].Field == Obelisk::Core::StructureScalarField::BForce,
                    "CanSeat bForce field mismatch");
            Require(event.View.Scalars[0].BoolValue, "CanSeat bForce value mismatch");
            Require(event.View.Scalars[1].Field == Obelisk::Core::StructureScalarField::ReturnValue,
                    "CanSeat return field mismatch");
            Require(event.View.Scalars[1].BoolValue, "CanSeat return value mismatch");
        }
    }

    void TestRejectsNonCanonicalStructureBoolWithoutDispatchBudget()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 2;
        fixture.Params[0x05] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        CopiedStructureEvent event;
        Require(!TryBuildCopiedStructureEvent(attempt.Invocation, event),
                "copied SetVariant event accepted non-canonical bool");
        Require(event.View.Scalars.empty(), "failed non-canonical SetVariant left copied scalar span");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(attempt, dispatchCounter, 1, observationNumber),
                "non-canonical SetVariant consumed structure dispatch budget");
        Require(observationNumber == 0, "non-canonical SetVariant did not clear dispatch observation number");
        Require(dispatchCounter.load() == 0, "non-canonical SetVariant changed dispatch counter");

        int owner = 0;
        std::vector<CapturedStructureEvent> captured;
        const uint64_t registrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::StructureEventSubscription{CaptureStructureEvent, &captured});
        Require(registrationId != 0, "failed to register structure event callback");
        Require(MaybeDispatchCopiedStructureEventAfterOriginal(true, attempt.Invocation) == 0,
                "non-canonical SetVariant dispatched copied structure event");
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);
        Require(captured.empty(), "non-canonical SetVariant reached structure callback");
    }

    void TestRejectsShortStructureScalarRangeWithoutDispatchBudget()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        attempt.Invocation.Fields[0].Range.Size = 1;

        CopiedStructureEvent event;
        Require(!TryBuildCopiedStructureEvent(attempt.Invocation, event),
                "copied SetVariant event accepted a short int32 scalar range");
        Require(event.View.Scalars.empty(), "failed short-range SetVariant left copied scalar span");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(attempt, dispatchCounter, 1, observationNumber),
                "short-range SetVariant consumed structure dispatch budget");
        Require(observationNumber == 0, "short-range SetVariant did not clear dispatch observation number");
        Require(dispatchCounter.load() == 0, "short-range SetVariant changed dispatch counter");
    }

    void TestCopiedStructureEventRebindsScalarSpanOnCopyAndMove()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        CopiedStructureEvent event;
        Require(TryBuildCopiedStructureEvent(attempt.Invocation, event),
                "failed to build copied SetVariant event for copy test");

        CopiedStructureEvent copied = event;
        Require(copied.View.Scalars.data() == copied.ScalarStorage.data(),
                "copied structure event scalar span points to source storage");
        Require(copied.View.Scalars.size() == event.View.Scalars.size(),
                "copied structure event scalar span size mismatch");

        CopiedStructureEvent assigned;
        assigned = event;
        Require(assigned.View.Scalars.data() == assigned.ScalarStorage.data(),
                "assigned structure event scalar span points to source storage");

        CopiedStructureEvent moved = std::move(copied);
        Require(moved.View.Scalars.data() == moved.ScalarStorage.data(),
                "moved structure event scalar span points to source storage");
    }

    void TestDispatchUsesReservedCopiedStructureEvent()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t originalVariant = 11;
        WriteAt(fixture.Params, 0x00, originalVariant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        CopiedStructureEvent event;
        Require(TryBuildAndReserveDispatchBudgetForMatchedAttempt(
                    attempt, dispatchCounter, 1, observationNumber, event),
                "valid SetVariant did not reserve dispatch budget with copied event");
        const int32_t mutatedVariant = 99;
        WriteAt(fixture.Params, 0x00, mutatedVariant);
        fixture.Params[0x04] = 0;
        fixture.Params[0x05] = 1;

        int owner = 0;
        std::vector<CapturedStructureEvent> captured;
        const uint64_t registrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::StructureEventSubscription{CaptureStructureEvent, &captured});
        Require(registrationId != 0, "failed to register structure event callback");
        Require(MaybeDispatchCopiedStructureEventAfterOriginal(true, event) == 1,
                "copied reserved SetVariant did not dispatch");
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);

        Require(captured.size() == 1, "copied reserved SetVariant dispatch count mismatch");
        Require(captured[0].Scalars.size() == 3, "copied reserved SetVariant scalar count mismatch");
        Require(captured[0].Scalars[0].Int32Value == originalVariant,
                "copied reserved SetVariant read mutated params");
        Require(captured[0].Scalars[1].BoolValue,
                "copied reserved SetVariant bForceSet read mutated params");
        Require(!captured[0].Scalars[2].BoolValue,
                "copied reserved SetVariant ReturnValue read mutated params");
    }

    void TestDispatchesCopiedStructureEventThroughInternalDispatcher()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        int owner = 0;
        std::vector<CapturedStructureEvent> captured;
        const uint64_t registrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::StructureEventSubscription{CaptureStructureEvent, &captured});
        Require(registrationId != 0, "failed to register structure event callback");

        const size_t dispatched = MaybeDispatchCopiedStructureEventAfterOriginal(true, attempt.Invocation);
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);

        Require(dispatched == 1, "copied structure event was not dispatched");
        Require(captured.size() == 1, "captured structure event count mismatch");
        Require(captured[0].Kind == Obelisk::Core::StructureEventKind::SetVariant,
                "dispatched SetVariant kind mismatch");
        Require(captured[0].FunctionNameIndex == kSetVariantNameIndex,
                "dispatched SetVariant function index mismatch");
        Require(captured[0].OuterNameIndex == kPrimalStructureNameIndex,
                "dispatched SetVariant outer index mismatch");
        Require(captured[0].Scalars.size() == 3, "dispatched SetVariant scalar count mismatch");
        Require(captured[0].Scalars[0].Field == Obelisk::Core::StructureScalarField::VariantIndex,
                "dispatched SetVariant variant field mismatch");
        Require(captured[0].Scalars[0].Int32Value == variant, "dispatched SetVariant variant value mismatch");
        Require(captured[0].Scalars[1].Field == Obelisk::Core::StructureScalarField::BForceSet,
                "dispatched SetVariant bForceSet field mismatch");
        Require(captured[0].Scalars[1].BoolValue, "dispatched SetVariant bForceSet value mismatch");
        Require(captured[0].Scalars[2].Field == Obelisk::Core::StructureScalarField::ReturnValue,
                "dispatched SetVariant return field mismatch");
        Require(!captured[0].Scalars[2].BoolValue, "dispatched SetVariant return value mismatch");
    }

    void TestCopiedStructureDispatchRequiresOriginalProcessEvent()
    {
        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        int owner = 0;
        std::vector<CapturedStructureEvent> captured;
        const uint64_t registrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::StructureEventSubscription{CaptureStructureEvent, &captured});
        Require(registrationId != 0, "failed to register structure event callback");

        Require(MaybeDispatchCopiedStructureEventAfterOriginal(false, attempt.Invocation) == 0,
                "blocked original ProcessEvent still dispatched structure event");
        Require(captured.empty(), "blocked original ProcessEvent reached structure callback");
        Require(MaybeDispatchCopiedStructureEventAfterOriginal(true, attempt.Invocation) == 1,
                "post-original structure event did not dispatch");
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);

        Require(captured.size() == 1, "post-original structure event dispatch count mismatch");
        Require(captured[0].Kind == Obelisk::Core::StructureEventKind::SetVariant,
                "post-original SetVariant kind mismatch");
    }

    void TestBlockedPreCallbackPreventsIntegratedStructureDispatch()
    {
        g_BlockingPreCallbackCount = 0;
        g_OriginalProcessEventCallCount = 0;

        const fs::path root = MakeTempRoot();
        EnableProcessEventBlockingGate(root);

        StructureFixture fixture;
        BuildSetVariant(fixture);
        const int32_t variant = 11;
        WriteAt(fixture.Params, 0x00, variant);
        fixture.Params[0x04] = 1;
        fixture.Params[0x05] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kSetVariantNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        int preOwner = 0;
        int structureOwner = 0;
        std::vector<CapturedStructureEvent> captured;
        auto& eventManager = Obelisk::Core::EventManager::Get();
        const uint64_t preRegistrationId = eventManager.RegisterPreProcessEventForNameIndexOwned(
            &preOwner,
            kSetVariantNameIndex,
            BlockingPreCallback);
        const uint64_t structureRegistrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
            &structureOwner,
            Obelisk::Core::StructureEventSubscription{CaptureStructureEvent, &captured});
        Require(preRegistrationId != 0, "failed to register blocking pre-callback");
        Require(structureRegistrationId != 0, "failed to register structure event callback");

        const bool originalWasCalled = Obelisk::Hooks::DispatchProcessEventCallbacks(
            kSetVariantNameIndex,
            reinterpret_cast<void*>(0x1),
            fixture.Function.data(),
            fixture.Params.data(),
            true,
            false,
            CountOriginalProcessEventCall);
        const size_t dispatched =
            MaybeDispatchCopiedStructureEventAfterOriginal(originalWasCalled, attempt.Invocation);

        eventManager.UnregisterCallbacksForOwner(&preOwner);
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(&structureOwner);
        DisableProcessEventBlockingGate();
        fs::remove_all(root);

        Require(g_BlockingPreCallbackCount == 1, "blocking pre-callback did not run");
        Require(g_OriginalProcessEventCallCount == 0, "blocked pre-callback still called original ProcessEvent");
        Require(!originalWasCalled, "blocked dispatch reported that original ProcessEvent ran");
        Require(dispatched == 0, "blocked ProcessEvent dispatched copied structure event");
        Require(captured.empty(), "blocked ProcessEvent reached structure callback");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationLogLimit();
    TestReflectedStructureNameFilter();
    TestDisabledGateDoesNotRead();
    TestNonStructureNameDoesNotRead();
    TestIdentifyContainsReaderExceptions();
    TestRejectsPrefilterFunctionNameMismatch();
    TestGeneralIdentifyStillRecognizesVerifyPinCode();
    TestIdentifiesAllStructureHookTargets();
    TestNonPinExcludedTargetsDoNotReserveDispatchBudget();
    TestRejectsStructureHookWrongOuter();
    TestRejectsPinCodeCopiedStructureEventWithoutDispatchBudget();
    TestBuildsCopiedStructureEventForScalarStructureTargets();
    TestRejectsNonCanonicalStructureBoolWithoutDispatchBudget();
    TestRejectsShortStructureScalarRangeWithoutDispatchBudget();
    TestCopiedStructureEventRebindsScalarSpanOnCopyAndMove();
    TestDispatchUsesReservedCopiedStructureEvent();
    TestDispatchesCopiedStructureEventThroughInternalDispatcher();
    TestCopiedStructureDispatchRequiresOriginalProcessEvent();
    TestBlockedPreCallbackPreventsIntegratedStructureDispatch();

    std::cout << "ProcessEventStructureReflectionTests passed\n";
    return 0;
}
