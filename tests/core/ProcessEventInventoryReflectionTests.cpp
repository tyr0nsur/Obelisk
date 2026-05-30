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
    constexpr int32_t kServerRequestInventoryUseItemNameIndex = 2651;
    constexpr int32_t kServerRequestInventoryUseItemWithActorNameIndex = 2652;
    constexpr int32_t kPrimalItemNameIndex = 6231;
    constexpr int32_t kPrimalItemObjectIndex = 17;
    constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kInvCompNameIndex = 18798;
    constexpr int32_t kInventoryCompNameIndex = 16929;
    constexpr int32_t kByPCNameIndex = 18797;
    constexpr int32_t kBRequestedByPlayerNameIndex = 18796;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBIgnoreCooldownNameIndex = 18814;
    constexpr int32_t kItemIdNameIndex = 16928;
    constexpr int32_t kItemID1NameIndex = 16926;
    constexpr int32_t kAdditionalDataNameIndex = 19290;
    constexpr int32_t kAnActorNameIndex = 20098;
    constexpr uint32_t kAllowRemoteAddToInventoryFunctionFlags = 0x04020400;
    constexpr uint32_t kCanUseFunctionFlags = 0x54020400;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint64_t kRemoteAddInventoryComponentPropertyFlags = 0x1044080280;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;

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
        throw std::runtime_error("expected inventory reflection reader exception");
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
    }

    struct FieldDef
    {
        int32_t NameIndex = -1;
        int32_t Offset = -1;
        int32_t ElementSize = 0;
        const void* Class = nullptr;
        uint64_t PropertyFlags = 0;
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

    void PopulateFieldMetadata(InventoryReflection::InventoryFieldRange& field)
    {
        using InventoryReflection::InventoryField;
        switch (field.Field)
        {
        case InventoryField::BIgnoreCooldown:
        case InventoryField::BRequestedByPlayer:
            field.PropertyClassNameIndex = kBoolPropertyClassNameIndex;
            field.PropertyClassObjectIndex = kBoolPropertyClassObjectIndex;
            field.PropertyFlags = kBoolInputPropertyFlags;
            return;
        case InventoryField::ReturnValue:
            field.PropertyClassNameIndex = kBoolPropertyClassNameIndex;
            field.PropertyClassObjectIndex = kBoolPropertyClassObjectIndex;
            field.PropertyFlags = kBoolReturnPropertyFlags;
            return;
        case InventoryField::InventoryComponent:
            field.PropertyClassNameIndex = kObjectPropertyClassNameIndex;
            field.PropertyClassObjectIndex = kObjectPropertyClassObjectIndex;
            field.PropertyFlags =
                field.PropertyNameIndex == kInvCompNameIndex ? kRemoteAddInventoryComponentPropertyFlags
                                                             : kObjectInputPropertyFlags;
            return;
        case InventoryField::ByPC:
        case InventoryField::Actor:
            field.PropertyClassNameIndex = kObjectPropertyClassNameIndex;
            field.PropertyClassObjectIndex = kObjectPropertyClassObjectIndex;
            field.PropertyFlags = kObjectInputPropertyFlags;
            return;
        case InventoryField::RedactedItemId:
        case InventoryField::RedactedItemId1:
        case InventoryField::AdditionalData:
            return;
        }
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
        std::array<uint8_t, 0x40> FunctionClass{};
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
            Context.Regions.push_back({FunctionClass.data(), FunctionClass.size()});
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
                    kBoolPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
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
        WriteObject(fixture.Outer, kPrimalItemNameIndex, kPrimalItemObjectIndex, nullptr, nullptr);
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
                          {kBIgnoreCooldownNameIndex,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kReturnValueNameIndex,
                           0x01,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
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
                          {kInvCompNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kRemoteAddInventoryComponentPropertyFlags},
                          {kByPCNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBRequestedByPlayerNameIndex,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kReturnValueNameIndex,
                           0x11,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
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
        Require(!ShouldAttemptNameObservation(kServerRequestInventoryUseItemNameIndex, 1),
                "metadata-only ServerRequestInventoryUseItem FName should not pass observation filter");
        Require(!ShouldAttemptNameObservation(kServerRequestInventoryUseItemWithActorNameIndex, 1),
                "metadata-only ServerRequestInventoryUseItemWithActor FName should not pass observation filter");
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
        Require(!ShouldAttemptDispatchObservation(dispatchCounter, 1, 0),
                "inventory dispatch observation activated without subscribers");
        Require(ShouldAttemptDispatchObservation(dispatchCounter, 1, 1),
                "inventory dispatch observation did not activate with subscribers");

        Attempt rejectedAttempt;
        rejectedAttempt.Status = AttemptStatus::Rejected;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(rejectedAttempt, dispatchCounter, 1, observationNumber),
                "rejected inventory attempt consumed dispatch budget");
        Require(observationNumber == 0, "rejected dispatch attempt did not clear observation number");
        Require(dispatchCounter.load() == 0, "rejected inventory attempt changed dispatch counter");

        Attempt metadataOnlyMatchedAttempt;
        metadataOnlyMatchedAttempt.Status = AttemptStatus::Matched;
        metadataOnlyMatchedAttempt.Invocation.Function =
            InventoryReflection::InventoryFunction::ServerRequestInventoryUseItem;
        metadataOnlyMatchedAttempt.Invocation.FunctionNameIndex = kServerRequestInventoryUseItemNameIndex;
        metadataOnlyMatchedAttempt.Invocation.OuterNameIndex = kShooterPlayerControllerNameIndex;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(metadataOnlyMatchedAttempt,
                                                          dispatchCounter,
                                                          1,
                                                          observationNumber),
                "metadata-only inventory action consumed copied-bool dispatch budget");
        Require(observationNumber == 0, "metadata-only dispatch attempt did not clear observation number");
        Require(dispatchCounter.load() == 0, "metadata-only inventory action changed dispatch counter");

        Attempt wrongOuterMatchedAttempt;
        wrongOuterMatchedAttempt.Status = AttemptStatus::Matched;
        wrongOuterMatchedAttempt.Invocation.Function = InventoryReflection::InventoryFunction::CanUse;
        wrongOuterMatchedAttempt.Invocation.FunctionNameIndex = kCanUseNameIndex;
        wrongOuterMatchedAttempt.Invocation.OuterNameIndex = kShooterPlayerControllerNameIndex;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(wrongOuterMatchedAttempt,
                                                          dispatchCounter,
                                                          1,
                                                          observationNumber),
                "wrong-outer CanUse consumed copied-bool dispatch budget");
        Require(observationNumber == 0, "wrong-outer dispatch attempt did not clear observation number");
        Require(dispatchCounter.load() == 0, "wrong-outer CanUse changed dispatch counter");

        uint8_t ignoreCooldown = 1;
        uint8_t returnValue = 1;
        auto makeCanUseField = [](InventoryReflection::InventoryField field,
                                  int32_t propertyNameIndex,
                                  int32_t offset,
                                  const uint8_t* data) {
            InventoryReflection::InventoryFieldRange value;
            value.Field = field;
            value.PropertyNameIndex = propertyNameIndex;
            value.Offset = offset;
            value.Size = sizeof(uint8_t);
            value.ExposesRange = true;
            value.Range = {data, sizeof(uint8_t)};
            PopulateFieldMetadata(value);
            return value;
        };

        Attempt noParameterRangesMatchedAttempt;
        noParameterRangesMatchedAttempt.Status = AttemptStatus::Matched;
        noParameterRangesMatchedAttempt.Invocation.Function = InventoryReflection::InventoryFunction::CanUse;
        noParameterRangesMatchedAttempt.Invocation.FunctionNameIndex = kCanUseNameIndex;
        noParameterRangesMatchedAttempt.Invocation.OuterNameIndex = kPrimalItemNameIndex;
        noParameterRangesMatchedAttempt.Invocation.HasParameterRanges = false;
        noParameterRangesMatchedAttempt.Invocation.Fields.push_back(
            makeCanUseField(InventoryReflection::InventoryField::BIgnoreCooldown,
                            kBIgnoreCooldownNameIndex,
                            0x00,
                            &ignoreCooldown));
        noParameterRangesMatchedAttempt.Invocation.Fields.push_back(
            makeCanUseField(InventoryReflection::InventoryField::ReturnValue,
                            kReturnValueNameIndex,
                            0x01,
                            &returnValue));
        Require(!TryReserveDispatchBudgetForMatchedAttempt(noParameterRangesMatchedAttempt,
                                                          dispatchCounter,
                                                          1,
                                                          observationNumber),
                "CanUse without parameter ranges consumed copied-bool dispatch budget");
        Require(observationNumber == 0,
                "CanUse without parameter ranges did not clear dispatch observation number");
        Require(dispatchCounter.load() == 0,
                "CanUse without parameter ranges changed dispatch counter");

        Attempt wrongScalarShapeMatchedAttempt = noParameterRangesMatchedAttempt;
        wrongScalarShapeMatchedAttempt.Invocation.HasParameterRanges = true;
        wrongScalarShapeMatchedAttempt.Invocation.Fields[0].PropertyNameIndex = kReturnValueNameIndex;
        Require(!TryReserveDispatchBudgetForMatchedAttempt(wrongScalarShapeMatchedAttempt,
                                                          dispatchCounter,
                                                          1,
                                                          observationNumber),
                "wrong-shape CanUse consumed copied-bool dispatch budget");
        Require(observationNumber == 0, "wrong-shape CanUse did not clear dispatch observation number");
        Require(dispatchCounter.load() == 0, "wrong-shape CanUse changed dispatch counter");

        Attempt matchedAttempt;
        matchedAttempt.Status = AttemptStatus::Matched;
        matchedAttempt.Invocation.Function = InventoryReflection::InventoryFunction::CanUse;
        matchedAttempt.Invocation.FunctionNameIndex = kCanUseNameIndex;
        matchedAttempt.Invocation.OuterNameIndex = kPrimalItemNameIndex;
        matchedAttempt.Invocation.HasParameterRanges = true;
        matchedAttempt.Invocation.Fields.push_back(
            makeCanUseField(InventoryReflection::InventoryField::BIgnoreCooldown,
                            kBIgnoreCooldownNameIndex,
                            0x00,
                            &ignoreCooldown));
        matchedAttempt.Invocation.Fields.push_back(
            makeCanUseField(InventoryReflection::InventoryField::ReturnValue,
                            kReturnValueNameIndex,
                            0x01,
                            &returnValue));
        Require(TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "matched inventory attempt did not reserve dispatch budget");
        Require(observationNumber == 1, "matched dispatch observation number mismatch");
        Require(dispatchCounter.load() == 1, "matched inventory attempt did not advance dispatch counter");
        Require(!TryReserveDispatchBudgetForMatchedAttempt(matchedAttempt, dispatchCounter, 1, observationNumber),
                "exhausted matched dispatch budget reserved again");
        Require(observationNumber == 0, "exhausted matched dispatch budget did not clear observation number");
        Require(!HasObservationBudgetRemaining(dispatchCounter, 1),
                "exhausted inventory dispatch counter reported remaining budget");
        Require(!ShouldAttemptDispatchObservation(dispatchCounter, 1, 1),
                "exhausted inventory dispatch observation reported active with subscribers");
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

    void TestIdentifyContainsReaderExceptions()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            reinterpret_cast<void*>(0x20000));

        Require(attempt.Status == AttemptStatus::Rejected,
                "reader exception escaped inventory recognition as a non-rejection");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "reader exception did not fail closed as an implausible read");
    }

    void TestMetadataOnlyInventoryActionNamesDoNotRead()
    {
        constexpr int32_t metadataOnlyNames[] = {
            kServerRequestInventoryUseItemNameIndex,
            kServerRequestInventoryUseItemWithActorNameIndex,
        };

        for (int32_t nameIndex : metadataOnlyNames)
        {
            ReaderContext context;
            MemoryReader reader{RegionReader, &context};
            Attempt attempt = TryIdentifyInvocation(
                EnabledGate(),
                nameIndex,
                reader,
                reinterpret_cast<void*>(0x10000),
                reinterpret_cast<void*>(0x20000));

            Require(attempt.Status == AttemptStatus::NonInventoryFunction,
                    "metadata-only inventory action reached hook-side recognition");
            Require(context.Calls == 0, "metadata-only inventory action touched UFunction memory");
        }
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

    void TestCopiedInventoryPolicyEventCopyOwnsScalarSpan()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x01] = 0;

        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data());
        Require(attempt.Status == AttemptStatus::Matched, attempt.Result.Reason.c_str());

        CopiedInventoryPolicyEvent source;
        Require(TryBuildCopiedInventoryPolicyEvent(attempt.Invocation, source),
                "failed to build copied CanUse event for span ownership test");

        CopiedInventoryPolicyEvent copied = source;
        Require(copied.View.Scalars.data() == copied.ScalarStorage.data(),
                "copied inventory policy event scalar span points at source storage");
        source.ScalarStorage[0].BoolValue = false;
        Require(copied.View.Scalars[0].BoolValue,
                "copied inventory policy event scalar value aliased source storage");

        CopiedInventoryPolicyEvent assigned;
        assigned = copied;
        Require(assigned.View.Scalars.data() == assigned.ScalarStorage.data(),
                "assigned inventory policy event scalar span points at source storage");
        copied.ScalarStorage[1].BoolValue = true;
        Require(!assigned.View.Scalars[1].BoolValue,
                "assigned inventory policy event scalar value aliased source storage");
    }

    void TestCopiedInventoryPolicyEventsDoNotMutateParamsOrAliasRanges()
    {
        InventoryFixture canUseFixture;
        BuildCanUse(canUseFixture);
        canUseFixture.Params[0x00] = 1;
        canUseFixture.Params[0x01] = 0;
        const std::array<uint8_t, canUseFixture.Params.size()> canUseBefore = canUseFixture.Params;
        Attempt canUseAttempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanUseNameIndex,
            canUseFixture.Reader(),
            canUseFixture.Function.data(),
            canUseFixture.Params.data());
        Require(canUseAttempt.Status == AttemptStatus::Matched, canUseAttempt.Result.Reason.c_str());

        CopiedInventoryPolicyEvent canUseEvent;
        Require(TryBuildCopiedInventoryPolicyEvent(canUseAttempt.Invocation, canUseEvent),
                "failed to build copied CanUse event for mutation test");
        Require(canUseFixture.Params == canUseBefore, "CanUse event construction mutated params");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, canUseAttempt.Invocation) == 0,
                "CanUse dispatch without subscribers reported callbacks");
        Require(canUseFixture.Params == canUseBefore, "CanUse dispatch mutated params or return value");

        canUseFixture.Params[0x00] = 0;
        canUseFixture.Params[0x01] = 1;
        Require(canUseEvent.View.Scalars.size() == 2, "CanUse copied event scalar count changed");
        Require(canUseEvent.View.Scalars[0].BoolValue, "CanUse copied ignore-cooldown scalar aliased params");
        Require(!canUseEvent.View.Scalars[1].BoolValue, "CanUse copied return scalar aliased params");

        InventoryFixture remoteAddFixture;
        BuildAllowRemoteAdd(remoteAddFixture);
        remoteAddFixture.Params[0x10] = 0;
        remoteAddFixture.Params[0x11] = 1;
        const std::array<uint8_t, remoteAddFixture.Params.size()> remoteAddBefore = remoteAddFixture.Params;
        Attempt remoteAddAttempt = TryIdentifyInvocation(
            EnabledGate(),
            kAllowRemoteAddToInventoryNameIndex,
            remoteAddFixture.Reader(),
            remoteAddFixture.Function.data(),
            remoteAddFixture.Params.data());
        Require(remoteAddAttempt.Status == AttemptStatus::Matched, remoteAddAttempt.Result.Reason.c_str());

        CopiedInventoryPolicyEvent remoteAddEvent;
        Require(TryBuildCopiedInventoryPolicyEvent(remoteAddAttempt.Invocation, remoteAddEvent),
                "failed to build copied AllowRemoteAddToInventory event for mutation test");
        Require(remoteAddFixture.Params == remoteAddBefore,
                "AllowRemoteAddToInventory event construction mutated params");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, remoteAddAttempt.Invocation) == 0,
                "AllowRemoteAddToInventory dispatch without subscribers reported callbacks");
        Require(remoteAddFixture.Params == remoteAddBefore,
                "AllowRemoteAddToInventory dispatch mutated params or return value");

        remoteAddFixture.Params[0x10] = 1;
        remoteAddFixture.Params[0x11] = 0;
        Require(remoteAddEvent.View.Scalars.size() == 2,
                "AllowRemoteAddToInventory copied event scalar count changed");
        Require(!remoteAddEvent.View.Scalars[0].BoolValue,
                "AllowRemoteAddToInventory copied requested-by-player scalar aliased params");
        Require(remoteAddEvent.View.Scalars[1].BoolValue,
                "AllowRemoteAddToInventory copied return scalar aliased params");
    }

    void TestRejectsMetadataOnlyInventoryActionDispatch()
    {
        int owner = 0;
        std::vector<CapturedInventoryPolicyEvent> captured;
        const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::InventoryPolicyEventSubscription{CaptureInventoryPolicyEvent, &captured});
        Require(registrationId != 0, "failed to register inventory policy event callback");

        InventoryReflection::InventoryInvocation invocation;
        invocation.Function = InventoryReflection::InventoryFunction::ServerRequestInventoryUseItem;
        invocation.FunctionNameIndex = kServerRequestInventoryUseItemNameIndex;
        invocation.OuterNameIndex = kShooterPlayerControllerNameIndex;
        invocation.HasParameterRanges = true;

        uint64_t inventoryComponent = 0x1111111122222222ULL;
        uint64_t itemId = 0x3333333344444444ULL;
        uint64_t actor = 0x5555555566666666ULL;
        int32_t additionalData = 0x77777777;

        auto makeField = [](InventoryReflection::InventoryField field,
                            int32_t propertyNameIndex,
                            int32_t offset,
                            const void* data,
                            size_t size) {
            InventoryReflection::InventoryFieldRange value;
            value.Field = field;
            value.PropertyNameIndex = propertyNameIndex;
            value.Offset = offset;
            value.Size = size;
            value.ExposesRange = true;
            value.Range = {static_cast<const uint8_t*>(data), size};
            return value;
        };
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::InventoryComponent,
                                             kInventoryCompNameIndex,
                                             0x00,
                                             &inventoryComponent,
                                             sizeof(inventoryComponent)));
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::RedactedItemId,
                                             kItemIdNameIndex,
                                             0x08,
                                             &itemId,
                                             sizeof(itemId)));

        CopiedInventoryPolicyEvent event;
        Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "metadata-only ServerRequestInventoryUseItem converted to policy event");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, invocation) == 0,
                "metadata-only ServerRequestInventoryUseItem dispatched policy event");

        invocation.Function = InventoryReflection::InventoryFunction::ServerRequestInventoryUseItemWithActor;
        invocation.FunctionNameIndex = kServerRequestInventoryUseItemWithActorNameIndex;
        invocation.Fields.clear();
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::Actor,
                                             kAnActorNameIndex,
                                             0x00,
                                             &actor,
                                             sizeof(actor)));
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::InventoryComponent,
                                             kInventoryCompNameIndex,
                                             0x08,
                                             &inventoryComponent,
                                             sizeof(inventoryComponent)));
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::RedactedItemId1,
                                             kItemID1NameIndex,
                                             0x10,
                                             &itemId,
                                             sizeof(itemId)));
        invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::AdditionalData,
                                             kAdditionalDataNameIndex,
                                             0x18,
                                             &additionalData,
                                             sizeof(additionalData)));
        Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "metadata-only ServerRequestInventoryUseItemWithActor converted to policy event");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, invocation) == 0,
                "metadata-only ServerRequestInventoryUseItemWithActor dispatched policy event");

        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);
        Require(captured.empty(), "metadata-only inventory action reached internal/public event callbacks");
    }

    void TestRejectsDispatchWhenExpectedScalarsAreMissing()
    {
        InventoryReflection::InventoryInvocation invocation;
        invocation.Function = InventoryReflection::InventoryFunction::CanUse;
        invocation.FunctionNameIndex = kCanUseNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = true;

        CopiedInventoryPolicyEvent event;
        Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "CanUse policy event built without expected copied scalar fields");

        uint8_t returnValue = 1;
        InventoryReflection::InventoryFieldRange duplicateReturn;
        duplicateReturn.Field = InventoryReflection::InventoryField::ReturnValue;
        duplicateReturn.PropertyNameIndex = kReturnValueNameIndex;
        duplicateReturn.Offset = 0x01;
        duplicateReturn.Size = 0x01;
        duplicateReturn.ExposesRange = true;
        duplicateReturn.Range = {&returnValue, sizeof(returnValue)};
        PopulateFieldMetadata(duplicateReturn);
        invocation.Fields.push_back(duplicateReturn);
        invocation.Fields.push_back(duplicateReturn);

        Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "CanUse policy event built with duplicate ReturnValue instead of expected scalar shape");
    }

    void TestRejectsDispatchWithoutParameterRanges()
    {
        uint8_t ignoreCooldown = 1;
        uint8_t returnValue = 1;

        InventoryReflection::InventoryInvocation invocation;
        invocation.Function = InventoryReflection::InventoryFunction::CanUse;
        invocation.FunctionNameIndex = kCanUseNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = false;

        InventoryReflection::InventoryFieldRange ignoreField;
        ignoreField.Field = InventoryReflection::InventoryField::BIgnoreCooldown;
        ignoreField.PropertyNameIndex = kBIgnoreCooldownNameIndex;
        ignoreField.Offset = 0x00;
        ignoreField.Size = sizeof(uint8_t);
        ignoreField.ExposesRange = true;
        ignoreField.Range = {&ignoreCooldown, sizeof(ignoreCooldown)};
        PopulateFieldMetadata(ignoreField);
        invocation.Fields.push_back(ignoreField);

        InventoryReflection::InventoryFieldRange returnField;
        returnField.Field = InventoryReflection::InventoryField::ReturnValue;
        returnField.PropertyNameIndex = kReturnValueNameIndex;
        returnField.Offset = 0x01;
        returnField.Size = sizeof(uint8_t);
        returnField.ExposesRange = true;
        returnField.Range = {&returnValue, sizeof(returnValue)};
        PopulateFieldMetadata(returnField);
        invocation.Fields.push_back(returnField);

        CopiedInventoryPolicyEvent event;
        Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "CanUse policy event built from invocation without parameter-range ownership");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, invocation) == 0,
                "CanUse policy event dispatched from invocation without parameter-range ownership");
    }

    void TestRejectsDispatchWhenExpectedScalarMetadataDiffers()
    {
        uint8_t ignoreCooldown = 1;
        uint8_t returnValue = 1;

        auto makeBoolField = [](InventoryReflection::InventoryField field,
                                int32_t propertyNameIndex,
                                int32_t offset,
                                const uint8_t* data,
                                size_t rangeSize = sizeof(uint8_t)) {
            InventoryReflection::InventoryFieldRange value;
            value.Field = field;
            value.PropertyNameIndex = propertyNameIndex;
            value.Offset = offset;
            value.Size = sizeof(uint8_t);
            value.ExposesRange = true;
            value.Range = {data, rangeSize};
            PopulateFieldMetadata(value);
            return value;
        };

        auto makeCanUse = [&]() {
            InventoryReflection::InventoryInvocation invocation;
            invocation.Function = InventoryReflection::InventoryFunction::CanUse;
            invocation.FunctionNameIndex = kCanUseNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::BIgnoreCooldown,
                                                     kBIgnoreCooldownNameIndex,
                                                     0x00,
                                                     &ignoreCooldown));
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::ReturnValue,
                                                     kReturnValueNameIndex,
                                                     0x01,
                                                     &returnValue));
            return invocation;
        };

        CopiedInventoryPolicyEvent event;
        InventoryReflection::InventoryInvocation valid = makeCanUse();
        Require(TryBuildCopiedInventoryPolicyEvent(valid, event),
                "valid CanUse scalar metadata did not build a copied policy event");

        InventoryReflection::InventoryInvocation noParameterRanges = makeCanUse();
        noParameterRanges.HasParameterRanges = false;
        Require(!TryBuildCopiedInventoryPolicyEvent(noParameterRanges, event),
                "CanUse policy event built from invocation without parameter ranges");

        InventoryReflection::InventoryInvocation wrongOuter = makeCanUse();
        wrongOuter.OuterNameIndex = kShooterPlayerControllerNameIndex;
        Require(!TryBuildCopiedInventoryPolicyEvent(wrongOuter, event),
                "CanUse policy event built with wrong outer FName");

        InventoryReflection::InventoryInvocation wrongName = makeCanUse();
        wrongName.Fields[0].PropertyNameIndex = kReturnValueNameIndex;
        Require(!TryBuildCopiedInventoryPolicyEvent(wrongName, event),
                "CanUse policy event built with wrong scalar property FName");

        InventoryReflection::InventoryInvocation wrongOffset = makeCanUse();
        wrongOffset.Fields[1].Offset = 0x02;
        Require(!TryBuildCopiedInventoryPolicyEvent(wrongOffset, event),
                "CanUse policy event built with wrong scalar offset");

        InventoryReflection::InventoryInvocation wrongRangeSize = makeCanUse();
        wrongRangeSize.Fields[0].Range.Size = 0;
        Require(!TryBuildCopiedInventoryPolicyEvent(wrongRangeSize, event),
                "CanUse policy event built with wrong scalar range size");
    }

    void TestRejectsDispatchWhenPolicyFieldSequenceDiffers()
    {
        uint8_t ignoreCooldown = 1;
        uint8_t requestedByPlayer = 0;
        uint8_t returnValue = 1;

        auto makeBoolField = [](InventoryReflection::InventoryField field,
                                int32_t propertyNameIndex,
                                int32_t offset,
                                const uint8_t* data) {
            InventoryReflection::InventoryFieldRange value;
            value.Field = field;
            value.PropertyNameIndex = propertyNameIndex;
            value.Offset = offset;
            value.Size = sizeof(uint8_t);
            value.ExposesRange = true;
            value.Range = {data, sizeof(uint8_t)};
            PopulateFieldMetadata(value);
            return value;
        };

        auto makeSwappedCanUse = [&]() {
            InventoryReflection::InventoryInvocation invocation;
            invocation.Function = InventoryReflection::InventoryFunction::CanUse;
            invocation.FunctionNameIndex = kCanUseNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::ReturnValue,
                                                     kReturnValueNameIndex,
                                                     0x01,
                                                     &returnValue));
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::BIgnoreCooldown,
                                                     kBIgnoreCooldownNameIndex,
                                                     0x00,
                                                     &ignoreCooldown));
            return invocation;
        };

        auto makeSwappedRemoteAdd = [&]() {
            InventoryReflection::InventoryInvocation invocation;
            invocation.Function = InventoryReflection::InventoryFunction::AllowRemoteAddToInventory;
            invocation.FunctionNameIndex = kAllowRemoteAddToInventoryNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;

            InventoryReflection::InventoryFieldRange inventoryComponent;
            inventoryComponent.Field = InventoryReflection::InventoryField::InventoryComponent;
            inventoryComponent.PropertyNameIndex = kInvCompNameIndex;
            inventoryComponent.Offset = 0x00;
            inventoryComponent.Size = sizeof(uint64_t);
            inventoryComponent.ExposesRange = false;
            PopulateFieldMetadata(inventoryComponent);

            InventoryReflection::InventoryFieldRange byPc;
            byPc.Field = InventoryReflection::InventoryField::ByPC;
            byPc.PropertyNameIndex = kByPCNameIndex;
            byPc.Offset = 0x08;
            byPc.Size = sizeof(uint64_t);
            byPc.ExposesRange = false;
            PopulateFieldMetadata(byPc);

            invocation.Fields.push_back(inventoryComponent);
            invocation.Fields.push_back(byPc);
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::ReturnValue,
                                                     kReturnValueNameIndex,
                                                     0x11,
                                                     &returnValue));
            invocation.Fields.push_back(makeBoolField(InventoryReflection::InventoryField::BRequestedByPlayer,
                                                     kBRequestedByPlayerNameIndex,
                                                     0x10,
                                                     &requestedByPlayer));
            return invocation;
        };

        int owner = 0;
        std::vector<CapturedInventoryPolicyEvent> captured;
        const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::InventoryPolicyEventSubscription{CaptureInventoryPolicyEvent, &captured});
        Require(registrationId != 0, "failed to register inventory policy event callback for sequence test");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        CopiedInventoryPolicyEvent event;
        auto requireRejected = [&](const InventoryReflection::InventoryInvocation& invocation,
                                   const char* label) {
            Require(!TryBuildCopiedInventoryPolicyEvent(invocation, event), label);

            Attempt attempt;
            attempt.Status = AttemptStatus::Matched;
            attempt.Invocation = invocation;
            observationNumber = 99;
            Require(!TryReserveDispatchBudgetForMatchedAttempt(attempt,
                                                              dispatchCounter,
                                                              1,
                                                              observationNumber),
                    label);
            Require(observationNumber == 0, "wrong-sequence invocation did not clear dispatch observation number");
            Require(dispatchCounter.load() == 0, "wrong-sequence invocation consumed dispatch budget");
            Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, invocation) == 0,
                    "wrong-sequence invocation dispatched a copied policy event");
            Require(captured.empty(), "wrong-sequence invocation reached inventory policy callback");
        };

        requireRejected(makeSwappedCanUse(), "CanUse policy event built with swapped scalar sequence");
        requireRejected(makeSwappedRemoteAdd(),
                        "AllowRemoteAddToInventory policy event built with swapped scalar sequence");

        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);
    }

    void TestDoesNotCopySensitiveInventoryRangesFromForgedInvocation()
    {
        uint64_t inventoryComponent = 0x1111111122222222ULL;
        uint64_t byPc = 0x3333333344444444ULL;
        uint64_t itemId = 0x5555555566666666ULL;
        int32_t additionalData = 0x77777777;
        uint8_t requestedByPlayer = 1;
        uint8_t returnValue = 0;

        auto makeField = [](InventoryReflection::InventoryField field,
                            int32_t propertyNameIndex,
                            int32_t offset,
                            const void* data,
                            size_t size,
                            bool exposesRange = true) {
            InventoryReflection::InventoryFieldRange value;
            value.Field = field;
            value.PropertyNameIndex = propertyNameIndex;
            value.Offset = offset;
            value.Size = size;
            value.ExposesRange = exposesRange;
            if (exposesRange)
                value.Range = {static_cast<const uint8_t*>(data), size};
            PopulateFieldMetadata(value);
            return value;
        };

        auto makeValidRemoteAdd = [&]() {
            InventoryReflection::InventoryInvocation invocation;
            invocation.Function = InventoryReflection::InventoryFunction::AllowRemoteAddToInventory;
            invocation.FunctionNameIndex = kAllowRemoteAddToInventoryNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::InventoryComponent,
                                                 kInvCompNameIndex,
                                                 0x00,
                                                 &inventoryComponent,
                                                 sizeof(inventoryComponent),
                                                 false));
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::ByPC,
                                                 kByPCNameIndex,
                                                 0x08,
                                                 &byPc,
                                                 sizeof(byPc),
                                                 false));
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::BRequestedByPlayer,
                                                 kBRequestedByPlayerNameIndex,
                                                 0x10,
                                                 &requestedByPlayer,
                                                 sizeof(requestedByPlayer)));
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::ReturnValue,
                                                 kReturnValueNameIndex,
                                                 0x11,
                                                 &returnValue,
                                                 sizeof(returnValue)));
            return invocation;
        };

        auto makeValidCanUse = [&]() {
            InventoryReflection::InventoryInvocation invocation;
            invocation.Function = InventoryReflection::InventoryFunction::CanUse;
            invocation.FunctionNameIndex = kCanUseNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::BIgnoreCooldown,
                                                 kBIgnoreCooldownNameIndex,
                                                 0x00,
                                                 &requestedByPlayer,
                                                 sizeof(requestedByPlayer)));
            invocation.Fields.push_back(makeField(InventoryReflection::InventoryField::ReturnValue,
                                                 kReturnValueNameIndex,
                                                 0x01,
                                                 &returnValue,
                                                 sizeof(returnValue)));
            return invocation;
        };

        InventoryReflection::InventoryInvocation invocation = makeValidRemoteAdd();

        CopiedInventoryPolicyEvent event;
        Require(TryBuildCopiedInventoryPolicyEvent(invocation, event),
                "metadata-only object fields prevented copying allowed scalar-only policy event");
        Require(event.View.Scalars.size() == 2, "object metadata was copied into policy event");
        Require(event.View.Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                "unexpected first scalar after object metadata");
        Require(event.View.Scalars[0].BoolValue, "allowed bRequestedByPlayer scalar value mismatch");
        Require(event.View.Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "unexpected second scalar after object metadata");
        Require(!event.View.Scalars[1].BoolValue, "allowed return scalar value mismatch");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t observationNumber = 99;
        int owner = 0;
        std::vector<CapturedInventoryPolicyEvent> captured;
        const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::InventoryPolicyEventSubscription{CaptureInventoryPolicyEvent, &captured});
        Require(registrationId != 0, "failed to register inventory policy event callback for forged range test");

        auto requireNoBudgetOrDispatch = [&](const InventoryReflection::InventoryInvocation& forged,
                                             const char* label) {
            Attempt attempt;
            attempt.Status = AttemptStatus::Matched;
            attempt.Invocation = forged;
            observationNumber = 99;
            Require(!TryReserveDispatchBudgetForMatchedAttempt(attempt,
                                                              dispatchCounter,
                                                              1,
                                                              observationNumber),
                    label);
            Require(observationNumber == 0,
                    "forged inventory invocation did not clear dispatch observation number");
            Require(dispatchCounter.load() == 0,
                    "forged inventory invocation consumed dispatch budget");
            Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, forged) == 0,
                    "forged inventory invocation dispatched a copied policy event");
            Require(captured.empty(), "forged inventory invocation reached inventory policy callback");
        };

        InventoryReflection::InventoryInvocation forgedInventoryRange = makeValidRemoteAdd();
        forgedInventoryRange.Fields[0].ExposesRange = true;
        forgedInventoryRange.Fields[0].Range = {
            reinterpret_cast<const uint8_t*>(&inventoryComponent),
            sizeof(inventoryComponent),
        };
        Require(!TryBuildCopiedInventoryPolicyEvent(forgedInventoryRange, event),
                "forged InventoryComponent range built a copied policy event");
        requireNoBudgetOrDispatch(forgedInventoryRange,
                                  "forged InventoryComponent range consumed copied-bool dispatch budget");

        InventoryReflection::InventoryInvocation forgedByPcRange = makeValidRemoteAdd();
        forgedByPcRange.Fields[1].ExposesRange = true;
        forgedByPcRange.Fields[1].Range = {
            reinterpret_cast<const uint8_t*>(&byPc),
            sizeof(byPc),
        };
        Require(!TryBuildCopiedInventoryPolicyEvent(forgedByPcRange, event),
                "forged ByPC range built a copied policy event");
        requireNoBudgetOrDispatch(forgedByPcRange,
                                  "forged ByPC range consumed copied-bool dispatch budget");

        InventoryReflection::InventoryInvocation additionalDataInvocation;
        additionalDataInvocation.Function = InventoryReflection::InventoryFunction::AllowRemoteAddToInventory;
        additionalDataInvocation.FunctionNameIndex = kAllowRemoteAddToInventoryNameIndex;
        additionalDataInvocation.OuterNameIndex = kPrimalItemNameIndex;
        additionalDataInvocation.HasParameterRanges = true;
        additionalDataInvocation.Fields.push_back(makeField(InventoryReflection::InventoryField::AdditionalData,
                                                           kAdditionalDataNameIndex,
                                                           0x00,
                                                           &additionalData,
                                                           sizeof(additionalData)));
        additionalDataInvocation.Fields.push_back(makeField(InventoryReflection::InventoryField::RedactedItemId1,
                                                           kItemID1NameIndex,
                                                           0x08,
                                                           &itemId,
                                                           sizeof(itemId)));
        additionalDataInvocation.Fields.push_back(makeField(InventoryReflection::InventoryField::BRequestedByPlayer,
                                                           kBRequestedByPlayerNameIndex,
                                                           0x10,
                                                           &requestedByPlayer,
                                                           sizeof(requestedByPlayer)));
        additionalDataInvocation.Fields.push_back(makeField(InventoryReflection::InventoryField::ReturnValue,
                                                           kReturnValueNameIndex,
                                                           0x11,
                                                           &returnValue,
                                                           sizeof(returnValue)));

        Require(!TryBuildCopiedInventoryPolicyEvent(additionalDataInvocation, event),
                "AdditionalData or ItemID1 range built a copied policy event");
        requireNoBudgetOrDispatch(additionalDataInvocation,
                                  "AdditionalData or ItemID1 range consumed copied-bool dispatch budget");

        InventoryReflection::InventoryInvocation forgedCanUseObjectRef = makeValidCanUse();
        forgedCanUseObjectRef.Fields.push_back(makeField(InventoryReflection::InventoryField::InventoryComponent,
                                                        kInventoryCompNameIndex,
                                                        0x08,
                                                        &inventoryComponent,
                                                        sizeof(inventoryComponent)));
        Require(!TryBuildCopiedInventoryPolicyEvent(forgedCanUseObjectRef, event),
                "forged CanUse object ref built a copied policy event");
        requireNoBudgetOrDispatch(forgedCanUseObjectRef,
                                  "forged CanUse object ref consumed copied-bool dispatch budget");

        InventoryReflection::InventoryInvocation forgedCanUseSensitiveFields = makeValidCanUse();
        forgedCanUseSensitiveFields.Fields.push_back(makeField(InventoryReflection::InventoryField::RedactedItemId,
                                                              kItemIdNameIndex,
                                                              0x08,
                                                              &itemId,
                                                              sizeof(itemId)));
        forgedCanUseSensitiveFields.Fields.push_back(makeField(InventoryReflection::InventoryField::AdditionalData,
                                                              kAdditionalDataNameIndex,
                                                              0x10,
                                                              &additionalData,
                                                              sizeof(additionalData)));
        Require(!TryBuildCopiedInventoryPolicyEvent(forgedCanUseSensitiveFields, event),
                "forged CanUse ItemId or AdditionalData built a copied policy event");
        requireNoBudgetOrDispatch(forgedCanUseSensitiveFields,
                                  "forged CanUse ItemId or AdditionalData consumed copied-bool dispatch budget");

        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);
    }

    Attempt BuildMatchedAttempt(InventoryFixture& fixture, int32_t nameIndex)
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

    void TestDispatchesCopiedInventoryPolicyEventsThroughInternalDispatcher()
    {
        InventoryFixture canUseFixture;
        BuildCanUse(canUseFixture);
        canUseFixture.Params[0x00] = 0;
        canUseFixture.Params[0x01] = 1;
        Attempt canUseAttempt = BuildMatchedAttempt(canUseFixture, kCanUseNameIndex);

        InventoryFixture remoteAddFixture;
        BuildAllowRemoteAdd(remoteAddFixture);
        remoteAddFixture.Params[0x10] = 1;
        remoteAddFixture.Params[0x11] = 0;
        Attempt remoteAddAttempt = BuildMatchedAttempt(remoteAddFixture, kAllowRemoteAddToInventoryNameIndex);

        int owner = 0;
        std::vector<CapturedInventoryPolicyEvent> captured;
        const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
            &owner,
            Obelisk::Core::InventoryPolicyEventSubscription{CaptureInventoryPolicyEvent, &captured});
        Require(registrationId != 0, "failed to register inventory policy event callback");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t dispatchObservationNumber = 0;
        CopiedInventoryPolicyEvent copiedCanUseEvent;
        Require(TryBuildAndReserveDispatchBudgetForMatchedAttempt(canUseAttempt,
                                                                   dispatchCounter,
                                                                   1,
                                                                   dispatchObservationNumber,
                                                                   copiedCanUseEvent),
                "matched CanUse attempt did not build copied event and reserve dispatch budget");
        Require(dispatchObservationNumber == 1, "copied CanUse dispatch observation number mismatch");
        Require(!TryBuildAndReserveDispatchBudgetForMatchedAttempt(canUseAttempt,
                                                                   dispatchCounter,
                                                                   1,
                                                                   dispatchObservationNumber,
                                                                   copiedCanUseEvent),
                "exhausted copied CanUse dispatch budget still returned an event");
        Require(copiedCanUseEvent.View.Scalars.empty(),
                "exhausted dispatch budget left a stale copied inventory policy event");
        Require(TryBuildAndReserveDispatchBudgetForMatchedAttempt(canUseAttempt,
                                                                   dispatchCounter,
                                                                   2,
                                                                   dispatchObservationNumber,
                                                                   copiedCanUseEvent),
                "matched CanUse attempt did not rebuild copied event after exhausted budget");
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(false, copiedCanUseEvent) == 0,
                "blocked original ProcessEvent still dispatched inventory policy event");
        Require(captured.empty(), "blocked original ProcessEvent reached inventory policy callback");
        canUseFixture.Params[0x00] = 1;
        canUseFixture.Params[0x01] = 0;
        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, copiedCanUseEvent) == 1,
                "post-original inventory policy event did not dispatch");

        Require(MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(true, remoteAddAttempt.Invocation) == 1,
                "post-original remote-add inventory policy event did not dispatch");
        remoteAddFixture.Params[0x10] = 0;
        remoteAddFixture.Params[0x11] = 1;

        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(&owner);

        Require(captured.size() == 2, "captured inventory policy event count mismatch");
        Require(captured[0].Kind == Obelisk::Core::InventoryPolicyEventKind::CanUse,
                "dispatched CanUse kind mismatch");
        Require(captured[0].Scalars.size() == 2, "dispatched CanUse scalar count mismatch");
        Require(captured[0].Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BIgnoreCooldown,
                "dispatched bIgnoreCooldown field mismatch");
        Require(!captured[0].Scalars[0].BoolValue, "dispatched bIgnoreCooldown value mismatch");
        Require(captured[0].Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "dispatched return field mismatch");
        Require(captured[0].Scalars[1].BoolValue, "dispatched return value mismatch");

        Require(captured[1].Kind == Obelisk::Core::InventoryPolicyEventKind::AllowRemoteAddToInventory,
                "dispatched AllowRemoteAddToInventory kind mismatch");
        Require(captured[1].Scalars.size() == 2, "dispatched remote-add scalar count mismatch");
        Require(captured[1].Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                "dispatched bRequestedByPlayer field mismatch");
        Require(captured[1].Scalars[0].BoolValue, "dispatched bRequestedByPlayer value was not copied");
        Require(captured[1].Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "dispatched remote-add return field mismatch");
        Require(!captured[1].Scalars[1].BoolValue, "dispatched remote-add return value was not copied");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationBudgetAndFilter();
    TestDisabledGateDoesNotRead();
    TestNonInventoryNameDoesNotRead();
    TestIdentifyContainsReaderExceptions();
    TestMetadataOnlyInventoryActionNamesDoNotRead();
    TestIdentifiesCanUse();
    TestIdentifiesAllowRemoteAddWithoutObjectRanges();
    TestBuildsCopiedInventoryPolicyEventWithoutObjectFields();
    TestBuildsCopiedInventoryPolicyEventForCanUse();
    TestCopiedInventoryPolicyEventCopyOwnsScalarSpan();
    TestCopiedInventoryPolicyEventsDoNotMutateParamsOrAliasRanges();
    TestRejectsMetadataOnlyInventoryActionDispatch();
    TestRejectsDispatchWhenExpectedScalarsAreMissing();
    TestRejectsDispatchWithoutParameterRanges();
    TestRejectsDispatchWhenExpectedScalarMetadataDiffers();
    TestRejectsDispatchWhenPolicyFieldSequenceDiffers();
    TestDoesNotCopySensitiveInventoryRangesFromForgedInvocation();
    TestDispatchesCopiedInventoryPolicyEventsThroughInternalDispatcher();

    std::cout << "ProcessEventInventoryReflectionTests passed\n";
    return 0;
}
