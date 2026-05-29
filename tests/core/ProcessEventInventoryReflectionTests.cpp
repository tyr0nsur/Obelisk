#include "hooks/ProcessEventInventoryReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventInventoryReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kAllowRemoteAddToInventoryNameIndex = 6236;
    constexpr int32_t kCanUseNameIndex = 6252;
    constexpr int32_t kPrimalItemNameIndex = 6231;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kInvCompNameIndex = 18798;
    constexpr int32_t kByPCNameIndex = 18797;
    constexpr int32_t kBRequestedByPlayerNameIndex = 18796;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBIgnoreCooldownNameIndex = 18814;
    constexpr uint32_t kAllowRemoteAddToInventoryFunctionFlags = 0x04020400;
    constexpr uint32_t kCanUseFunctionFlags = 0x54020400;

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

    struct FieldDef
    {
        int32_t NameIndex = -1;
        int32_t Offset = -1;
        int32_t ElementSize = 0;
        const void* Class = nullptr;
    };

    struct CapturedInventoryPolicyEvent
    {
        Obelisk::Core::InventoryPolicyEventKind Kind = Obelisk::Core::InventoryPolicyEventKind::CanUse;
        std::vector<Obelisk::Core::InventoryPolicyScalarValue> Scalars;
    };

    void CaptureInventoryPolicyEvent(const Obelisk::Core::InventoryPolicyEventView& event, void* userData)
    {
        auto* captured = static_cast<std::vector<CapturedInventoryPolicyEvent>*>(userData);
        captured->push_back({
            event.Kind,
            std::vector<Obelisk::Core::InventoryPolicyScalarValue>(event.Scalars.begin(), event.Scalars.end()),
        });
    }

    struct InventoryFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
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
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return {GateStatus::Enabled, std::string(kSupportedShooterGameServerSha256)};
    }

    void InitClasses(InventoryFixture& fixture)
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
    }

    void BuildFunction(InventoryFixture& fixture,
                       int32_t functionNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 4>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kPrimalItemNameIndex, kPrimalItemNameIndex, nullptr, nullptr);
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

        WriteAt(fixture.Function, 0x38, fixture.PropertyA.data());
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildCanUse(InventoryFixture& fixture)
    {
        BuildFunction(fixture,
                      kCanUseNameIndex,
                      kCanUseFunctionFlags,
                      2,
                      0x02,
                      0x01,
                      {{
                          {kBIgnoreCooldownNameIndex, 0x00, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x01, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                          {},
                      }});
    }

    void BuildAllowRemoteAdd(InventoryFixture& fixture)
    {
        BuildFunction(fixture,
                      kAllowRemoteAddToInventoryNameIndex,
                      kAllowRemoteAddToInventoryFunctionFlags,
                      4,
                      0x12,
                      0x11,
                      {{
                          {kInvCompNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kByPCNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data()},
                          {kBRequestedByPlayerNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x11, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void TestGateEvaluation()
    {
        const char* supportedSha = kSupportedShooterGameServerSha256.data();

        Require(EvaluateGate(nullptr, true, true, true, supportedSha).Status == GateStatus::Disabled,
                "missing enable env should disable inventory reflection");
        Require(EvaluateGate("0", true, true, true, supportedSha).Status == GateStatus::Disabled,
                "non-1 enable env should disable inventory reflection");
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
        Require(gate.Status == GateStatus::Enabled, "supported inventory reflection gate did not enable");
        Require(gate.Enabled(), "enabled inventory reflection gate did not report enabled");
    }

    void TestObservationBudgetAndFilter()
    {
        Require(!ShouldAttemptObservation(0), "zero inventory reflection log limit should skip observation");
        Require(ShouldAttemptObservation(1), "non-zero inventory reflection log limit should allow observation");
        Require(ShouldAttemptNameObservation(kCanUseNameIndex, 1), "CanUse FName should pass observation filter");
        Require(ShouldAttemptNameObservation(kAllowRemoteAddToInventoryNameIndex, 1),
                "AllowRemoteAddToInventory FName should pass observation filter");
        Require(!ShouldAttemptNameObservation(42, 1), "non-inventory FName should not pass observation filter");
        Require(!ShouldAttemptNameObservation(kCanUseNameIndex, 0), "zero budget should skip matching FName");
        Require(ShouldAttemptNameObservation(kCanUseNameIndex, 0, 1),
                "dispatch budget should allow inventory observation without log budget");
        Require(!ShouldAttemptNameObservation(kCanUseNameIndex, 0, 0),
                "zero log and dispatch budgets should skip inventory observation");

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Require(!TryReserveObservationBudget(counter, 0, observationNumber), "zero limit reserved budget");
        Require(observationNumber == 0, "zero limit did not clear observation number");
        Require(TryReserveObservationBudget(counter, 1, observationNumber), "first reservation failed");
        Require(observationNumber == 1, "first observation number mismatch");
        Require(!TryReserveObservationBudget(counter, 1, observationNumber), "budget reservation exceeded limit");
        Require(counter.load() == 1, "budget counter mismatch");

        std::atomic<uint64_t> logCounter{0};
        std::atomic<uint64_t> dispatchCounter{0};
        Require(!ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 0),
                "zero log and dispatch budgets reported active runtime observation");
        Require(ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 1),
                "dispatch budget did not activate runtime observation");
        Require(HasObservationBudgetRemaining(dispatchCounter, 1),
                "fresh inventory dispatch counter did not report remaining budget");

        Attempt rejectedAttempt;
        rejectedAttempt.Status = AttemptStatus::Rejected;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(rejectedAttempt, dispatchCounter, 1, observationNumber),
                "rejected inventory attempt consumed dispatch budget");
        Require(observationNumber == 0, "rejected dispatch attempt did not clear observation number");
        Require(dispatchCounter.load() == 0, "rejected inventory attempt changed dispatch counter");

        Attempt matchedAttempt;
        matchedAttempt.Status = AttemptStatus::Matched;
        Require(TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "matched inventory attempt did not reserve dispatch budget");
        Require(observationNumber == 1, "matched dispatch observation number mismatch");
        Require(dispatchCounter.load() == 1, "matched inventory attempt did not advance dispatch counter");
        Require(!TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "exhausted matched dispatch budget reserved again");
        Require(observationNumber == 0, "exhausted matched dispatch budget did not clear observation number");
        Require(!HasObservationBudgetRemaining(dispatchCounter, 1),
                "exhausted inventory dispatch counter reported remaining budget");
        Require(!ShouldAttemptRuntimeObservation(logCounter, 0, dispatchCounter, 1),
                "exhausted inventory dispatch budget still activated runtime observation");
    }

    void TestDisabledGateDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            {},
            kCanUseNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Disabled, "disabled gate did not short-circuit");
        Require(context.Calls == 0, "disabled gate touched UFunction memory");
    }

    void TestNonInventoryNameDoesNotRead()
    {
        ReaderContext context;
        MemoryReader reader{RegionReader, &context};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            42,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::NonInventoryFunction,
                "non-inventory name did not short-circuit");
        Require(context.Calls == 0, "non-inventory name touched UFunction memory");
    }

    void TestIdentifiesCanUse()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);
        fixture.Params[0] = 1;
        fixture.Params[1] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(attempt.Invocation.Function == InventoryReflection::InventoryFunction::CanUse,
                "CanUse function mismatch");
        Require(attempt.Invocation.Fields.size() == 2, "CanUse field count mismatch");
        Require(attempt.Invocation.Fields[0].Field == InventoryReflection::InventoryField::BIgnoreCooldown,
                "bIgnoreCooldown field mismatch");
        Require(attempt.Invocation.Fields[1].Field == InventoryReflection::InventoryField::ReturnValue,
                "ReturnValue field mismatch");
    }

    void TestIdentifiesAllowRemoteAddWithoutObjectRanges()
    {
        InventoryFixture fixture;
        BuildAllowRemoteAdd(fixture);
        fixture.Params[0x10] = 1;
        fixture.Params[0x11] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kAllowRemoteAddToInventoryNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());

        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());
        Require(attempt.Invocation.Function == InventoryReflection::InventoryFunction::AllowRemoteAddToInventory,
                "AllowRemoteAddToInventory function mismatch");
        Require(attempt.Invocation.Fields.size() == 4, "AllowRemoteAddToInventory field count mismatch");
        Require(attempt.Invocation.Fields[0].Range.Data == nullptr, "InventoryComponent range was exposed");
        Require(attempt.Invocation.Fields[1].Range.Data == nullptr, "ByPC range was exposed");
        Require(attempt.Invocation.Fields[2].Range.Data == fixture.Params.data() + 0x10,
                "bRequestedByPlayer range mismatch");
        Require(attempt.Invocation.Fields[3].Range.Data == fixture.Params.data() + 0x11,
                "ReturnValue range mismatch");
    }

    void TestBuildsCopiedInventoryPolicyEventWithoutObjectFields()
    {
        InventoryFixture fixture;
        BuildAllowRemoteAdd(fixture);
        fixture.Params[0x10] = 1;
        fixture.Params[0x11] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kAllowRemoteAddToInventoryNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        CopiedInventoryPolicyEvent event;
        Require(TryBuildCopiedInventoryPolicyEvent(attempt.Invocation, event),
                "failed to build copied AllowRemoteAddToInventory event");
        fixture.Params[0x10] = 0;
        fixture.Params[0x11] = 1;

        Require(event.View.Kind == Obelisk::Core::InventoryPolicyEventKind::AllowRemoteAddToInventory,
                "AllowRemoteAddToInventory event kind mismatch");
        Require(event.View.Scalars.size() == 2,
                "AllowRemoteAddToInventory copied object/player fields");
        Require(event.View.Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                "bRequestedByPlayer field mismatch");
        Require(event.View.Scalars[0].BoolValue, "bRequestedByPlayer value was not copied");
        Require(event.View.Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "return field mismatch");
        Require(!event.View.Scalars[1].BoolValue, "return value was not copied");
    }

    void TestBuildsCopiedInventoryPolicyEventForCanUse()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x01] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        CopiedInventoryPolicyEvent event;
        Require(TryBuildCopiedInventoryPolicyEvent(attempt.Invocation, event),
                "failed to build copied CanUse event");
        Require(event.View.Kind == Obelisk::Core::InventoryPolicyEventKind::CanUse,
                "CanUse event kind mismatch");
        Require(event.View.Scalars.size() == 2, "CanUse scalar count mismatch");
        Require(event.View.Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BIgnoreCooldown,
                "bIgnoreCooldown field mismatch");
        Require(event.View.Scalars[0].BoolValue, "bIgnoreCooldown value mismatch");
        Require(event.View.Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "return field mismatch");
        Require(event.View.Scalars[1].BoolValue, "return value mismatch");
    }

    void TestDispatchesCopiedInventoryPolicyEventThroughInternalDispatcher()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);
        fixture.Params[0x00] = 0;
        fixture.Params[0x01] = 1;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        int owner = 0;
        std::vector<CapturedInventoryPolicyEvent> captured;
        const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::InventoryPolicyEventSubscription{CaptureInventoryPolicyEvent, &captured});
        Require(registrationId != 0, "failed to register inventory policy event callback");

        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(false, attempt.Invocation) == 0,
                "blocked original ProcessEvent still dispatched inventory policy event");
        Require(captured.empty(), "blocked original ProcessEvent reached inventory policy callback");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, attempt.Invocation) == 1,
                "post-original inventory policy event did not dispatch");
        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);

        Require(captured.size() == 1, "captured inventory policy event count mismatch");
        Require(captured[0].Kind == Obelisk::Core::InventoryPolicyEventKind::CanUse,
                "dispatched CanUse kind mismatch");
        Require(captured[0].Scalars.size() == 2, "dispatched CanUse scalar count mismatch");
        Require(captured[0].Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BIgnoreCooldown,
                "dispatched bIgnoreCooldown field mismatch");
        Require(!captured[0].Scalars[0].BoolValue, "dispatched bIgnoreCooldown value mismatch");
        Require(captured[0].Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "dispatched return field mismatch");
        Require(captured[0].Scalars[1].BoolValue, "dispatched return value mismatch");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationBudgetAndFilter();
    TestDisabledGateDoesNotRead();
    TestNonInventoryNameDoesNotRead();
    TestIdentifiesCanUse();
    TestIdentifiesAllowRemoteAddWithoutObjectRanges();
    TestBuildsCopiedInventoryPolicyEventWithoutObjectFields();
    TestBuildsCopiedInventoryPolicyEventForCanUse();
    TestDispatchesCopiedInventoryPolicyEventThroughInternalDispatcher();

    std::cout << "ProcessEventInventoryReflectionTests passed\n";
    return 0;
}
