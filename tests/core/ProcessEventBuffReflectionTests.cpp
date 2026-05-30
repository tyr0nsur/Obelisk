#include "hooks/ProcessEventBuffReflection.h"

#include <atomic>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventBuffReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kAllowPostProcessEffectNameIndex = 1073;
    constexpr int32_t kBPOnBuffLifetimeUpdatedNameIndex = 1129;
    constexpr int32_t kBPBuffPreventUploadingNameIndex = 1236;
    constexpr int32_t kBPCustomAllowAddBuffNameIndex = 1288;
    constexpr int32_t kBPPreventAddingOtherBuffNameIndex = 1690;
    constexpr int32_t kBuffOverrideInventoryAccessInputNameIndex = 1814;
    constexpr int32_t kPrimalBuffNameIndex = 7843;
    constexpr int32_t kPrimalBuffObjectIndex = 195;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kClassPropertyClassNameIndex = 8;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kClassPropertyClassObjectIndex = 535;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kForCharacterNameIndex = 17726;
    constexpr int32_t kDamageCauserNameIndex = 19001;
    constexpr int32_t kAnotherBuffClassNameIndex = 24180;
    constexpr int32_t kBInputPressedNameIndex = 24188;
    constexpr int32_t kInControllerNameIndex = 24189;
    constexpr uint32_t kBuffEventFunctionFlags = 0x0c020800;
    constexpr uint32_t kBuffEventWithReturnFunctionFlags = 0x0c020c00;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;

    static_assert(std::is_standard_layout_v<BuffBoolObservation>,
                  "copied buff bool observations must keep a simple C-compatible layout");
    static_assert(std::is_trivially_copyable_v<BuffBoolObservation>,
                  "copied buff bool observations must remain byte-copyable");
    static_assert(std::is_standard_layout_v<CopiedBuffObservation>,
                  "copied buff observations must keep a simple C-compatible layout");
    static_assert(std::is_trivially_copyable_v<CopiedBuffObservation>,
                  "copied buff observations must remain byte-copyable");

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

    bool CountingReader(const void*, size_t, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
        ++reader->Calls;
        return false;
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("expected buff reflection reader exception");
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

    struct BuffFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> ClassPropertyClass{};
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
            Context.Regions.push_back({ObjectPropertyClass.data(), ObjectPropertyClass.size()});
            Context.Regions.push_back({BoolPropertyClass.data(), BoolPropertyClass.size()});
            Context.Regions.push_back({ClassPropertyClass.data(), ClassPropertyClass.size()});
            Context.Regions.push_back({FunctionClass.data(), FunctionClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    Gate EnabledGate()
    {
        return EvaluateGate("1", true, true, true, kSupportedShooterGameServerSha256.data());
    }

    void InitClasses(BuffFixture& fixture)
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
        WriteObject(fixture.ClassPropertyClass,
                    kClassPropertyClassNameIndex,
                    kClassPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(BuffFixture& fixture,
                       int32_t functionNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 3>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kPrimalBuffNameIndex, kPrimalBuffObjectIndex, nullptr, nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());

        std::array<std::array<uint8_t, 0x80>*, 3> properties{
            &fixture.PropertyA,
            &fixture.PropertyB,
            &fixture.PropertyC,
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

    void BuildBoolReturn(BuffFixture& fixture, int32_t functionNameIndex)
    {
        BuildFunction(fixture,
                      functionNameIndex,
                      kBuffEventWithReturnFunctionFlags,
                      1,
                      0x01,
                      0x00,
                      {{
                          {kReturnValueNameIndex, 0x00, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
    }

    void BuildZeroParam(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPOnBuffLifetimeUpdatedNameIndex,
                      kBuffEventFunctionFlags,
                      0,
                      0x00,
                      0xffff,
                      {{{}, {}, {}}});
    }

    void BuildBuffOverrideInventoryAccessInput(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBuffOverrideInventoryAccessInputNameIndex,
                      kBuffEventWithReturnFunctionFlags,
                      3,
                      0x0a,
                      0x09,
                      {{
                          {kInControllerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBInputPressedNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kReturnValueNameIndex, 0x09, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildBPCustomAllowAddBuff(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPCustomAllowAddBuffNameIndex,
                      kBuffEventFunctionFlags,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kForCharacterNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kDamageCauserNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kReturnValueNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildBPPreventAddingOtherBuff(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPPreventAddingOtherBuffNameIndex,
                      kBuffEventFunctionFlags,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kAnotherBuffClassNameIndex, 0x00, 0x08, fixture.ClassPropertyClass.data(), kObjectInputPropertyFlags},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                      }});
    }

    BuffReflection::BuffFieldRange MakeField(BuffReflection::BuffField field,
                                             int32_t propertyNameIndex,
                                             int32_t propertyClassNameIndex,
                                             int32_t propertyClassObjectIndex,
                                             uint64_t propertyFlags,
                                             int32_t offset,
                                             size_t size,
                                             bool exposesRange,
                                             const uint8_t* data = nullptr,
                                             size_t rangeSize = 0)
    {
        BuffReflection::BuffFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = propertyNameIndex;
        value.PropertyClassNameIndex = propertyClassNameIndex;
        value.PropertyClassObjectIndex = propertyClassObjectIndex;
        value.PropertyFlags = propertyFlags;
        value.Offset = offset;
        value.Size = size;
        value.ExposesRange = exposesRange;
        if (exposesRange)
            value.Range = {data, rangeSize};
        return value;
    }

    BuffReflection::BuffInvocation MakeBuffOverrideInvocation(uint8_t& inputPressed, uint8_t& returnValue)
    {
        BuffReflection::BuffInvocation invocation;
        invocation.Function = BuffReflection::BuffFunction::BuffOverrideInventoryAccessInput;
        invocation.FunctionNameIndex = kBuffOverrideInventoryAccessInputNameIndex;
        invocation.OuterNameIndex = kPrimalBuffNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(MakeField(BuffReflection::BuffField::InController,
                                              kInControllerNameIndex,
                                              kObjectPropertyClassNameIndex,
                                              kObjectPropertyClassObjectIndex,
                                              kObjectInputPropertyFlags,
                                              0x00,
                                              sizeof(uint64_t),
                                              false));
        invocation.Fields.push_back(MakeField(BuffReflection::BuffField::BInputPressed,
                                              kBInputPressedNameIndex,
                                              kBoolPropertyClassNameIndex,
                                              kBoolPropertyClassObjectIndex,
                                              kBoolInputPropertyFlags,
                                              0x08,
                                              sizeof(uint8_t),
                                              true,
                                              &inputPressed,
                                              sizeof(inputPressed)));
        invocation.Fields.push_back(MakeField(BuffReflection::BuffField::ReturnValue,
                                              kReturnValueNameIndex,
                                              kBoolPropertyClassNameIndex,
                                              kBoolPropertyClassObjectIndex,
                                              kBoolReturnPropertyFlags,
                                              0x09,
                                              sizeof(uint8_t),
                                              true,
                                              &returnValue,
                                              sizeof(returnValue)));
        return invocation;
    }

    void RequireRejected(const BuffReflection::BuffInvocation& invocation, const char* message)
    {
        CopiedBuffObservation observation;
        observation.BoolCount = 1;
        observation.BoolStorage[0].Field = BuffReflection::BuffField::ReturnValue;
        observation.BoolStorage[0].Value = true;

        Require(!TryBuildCopiedBuffObservation(invocation, observation), message);
        Require(observation.BoolCount == 0, "rejected copied buff observation left bool payload");
    }

    void RequireBool(const CopiedBuffObservation& observation,
                     size_t index,
                     BuffReflection::BuffField field,
                     bool value,
                     const char* message)
    {
        Require(index < observation.BoolCount, message);
        Require(observation.BoolStorage[index].Field == field, message);
        Require(observation.BoolStorage[index].Value == value, message);
    }

    void TestGateEvaluation()
    {
        Require(EvaluateGate(nullptr, true, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::Disabled,
                "missing buff env should disable gate");
        Require(EvaluateGate("0", true, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::Disabled,
                "non-one buff env should disable gate");
        Require(EvaluateGate("1", false, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingObserverDebugProfile,
                "missing observer profile was not reported");
        Require(EvaluateGate("1", true, false, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingObserverDebugWindow,
                "missing observer window was not reported");
        Require(EvaluateGate("1", true, true, false, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingInstanceMarker,
                "missing buff marker was not reported");
        Require(EvaluateGate("1", true, true, true, nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary hash was not reported");
        Require(EvaluateGate("1", true, true, true, "bad-sha").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary hash was not reported");

        Gate gate = EnabledGate();
        Require(gate.Enabled(), "valid buff gate did not enable");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "buff gate did not retain binary hash");
    }

    void TestObservationBudgetAndFilter()
    {
        Require(IsReflectedBuffNameIndex(kAllowPostProcessEffectNameIndex),
                "AllowPostProcessEffect name should be recognized");
        Require(IsReflectedBuffNameIndex(kBPOnBuffLifetimeUpdatedNameIndex),
                "BPOnBuffLifetimeUpdated name should be recognized");
        Require(IsReflectedBuffNameIndex(kBPBuffPreventUploadingNameIndex),
                "BPBuffPreventUploading name should be recognized");
        Require(IsReflectedBuffNameIndex(kBPCustomAllowAddBuffNameIndex),
                "BPCustomAllowAddBuff name should be recognized");
        Require(IsReflectedBuffNameIndex(kBPPreventAddingOtherBuffNameIndex),
                "BPPreventAddingOtherBuff name should be recognized");
        Require(IsReflectedBuffNameIndex(kBuffOverrideInventoryAccessInputNameIndex),
                "BuffOverrideInventoryAccessInput name should be recognized");
        Require(!IsReflectedBuffNameIndex(9999), "unknown buff name should not be recognized");

        Require(!ShouldAttemptObservation(0), "zero buff observation limit should disable observation");
        Require(ShouldAttemptObservation(1), "non-zero buff observation limit should enable observation");
        Require(ShouldAttemptNameObservation(kBuffOverrideInventoryAccessInputNameIndex, 1),
                "matching buff name and budget should pass filter");
        Require(!ShouldAttemptNameObservation(kBuffOverrideInventoryAccessInputNameIndex, 0),
                "zero buff budget should block matching name");
        Require(!ShouldAttemptNameObservation(9999, 1), "unknown buff name should not pass filter");

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Require(HasObservationBudgetRemaining(counter, 1), "initial buff budget should remain");
        Require(TryReserveObservationBudget(counter, 1, observationNumber), "failed to reserve buff budget");
        Require(observationNumber == 1, "wrong buff observation number");
        Require(!HasObservationBudgetRemaining(counter, 1), "exhausted buff budget reported remaining");
        Require(!TryReserveObservationBudget(counter, 1, observationNumber), "reserved exhausted buff budget");
        Require(observationNumber == 0, "exhausted buff budget left observation number set");
        Require(ShouldLogObservation(1, 1), "first buff observation should log");
        Require(!ShouldLogObservation(2, 1), "over-limit buff observation should not log");
    }

    void TestDisabledNonBuffAndZeroBudgetDoNotReadOrReserve()
    {
        ReaderContext context;
        MemoryReader reader{CountingReader, &context};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;

        Attempt disabled = TryObserveInvocation(
            {},
            kBuffOverrideInventoryAccessInputNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);
        Require(disabled.Status == AttemptStatus::Disabled, "disabled buff observation attempted read");
        Require(observationNumber == 0, "disabled buff observation left observation number set");
        Require(counter.load() == 0, "disabled buff observation reserved budget");
        Require(context.Calls == 0, "disabled buff observation read memory");

        observationNumber = 99;
        Attempt nonBuff = TryObserveInvocation(
            EnabledGate(),
            9999,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);
        Require(nonBuff.Status == AttemptStatus::NonBuffFunction,
                "non-buff observation was not rejected before budget");
        Require(observationNumber == 0, "non-buff observation left observation number set");
        Require(counter.load() == 0, "non-buff observation reserved budget");
        Require(context.Calls == 0, "non-buff observation read memory");

        observationNumber = 99;
        Attempt zeroBudget = TryObserveInvocation(
            EnabledGate(),
            kBuffOverrideInventoryAccessInputNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            0,
            observationNumber);
        Require(zeroBudget.Status == AttemptStatus::BudgetExhausted,
                "zero-budget buff observation did not fail closed before read");
        Require(observationNumber == 0, "zero-budget buff observation left observation number set");
        Require(counter.load() == 0, "zero-budget buff observation reserved budget");
        Require(context.Calls == 0, "zero-budget buff observation read memory");
    }

    void TestObserveContainsReaderExceptions()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Attempt attempt = TryObserveInvocation(
            EnabledGate(),
            kBuffOverrideInventoryAccessInputNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);
        Require(attempt.Status == AttemptStatus::Rejected, "throwing buff reader escaped bridge");
        Require(attempt.Result.Status == ReadStatus::Implausible, "throwing buff reader used wrong status");
        Require(counter.load() == 1, "matched-name throwing attempt did not consume reserved budget");
        Require(observationNumber == 1, "throwing attempt did not report reserved observation number");
    }

    void TestObserveMatchesAndBuildsCopiedObservation()
    {
        BuffFixture fixture;
        BuildBuffOverrideInventoryAccessInput(fixture);
        fixture.Params[0x08] = 1;
        fixture.Params[0x09] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Attempt attempt = TryObserveInvocation(
            EnabledGate(),
            kBuffOverrideInventoryAccessInputNameIndex,
            fixture.Reader(),
            fixture.Function.data(),
            fixture.Params.data(),
            counter,
            1,
            observationNumber);

        Require(attempt.Status == AttemptStatus::Matched, "valid buff invocation was not matched");
        Require(attempt.Invocation.FunctionNameIndex == kBuffOverrideInventoryAccessInputNameIndex,
                "matched buff invocation name mismatch");
        Require(attempt.Invocation.ParameterData == fixture.Params.data(), "matched buff parameter data was not kept");
        Require(attempt.Invocation.ParameterSize == 0x0a, "matched buff parameter size was not kept");
        Require(observationNumber == 1, "valid buff observation did not reserve number");

        CopiedBuffObservation observation;
        Require(TryBuildCopiedBuffObservationForMatchedAttempt(attempt, observation),
                "valid matched buff attempt did not build copied observation");
        Require(observation.Function == BuffReflection::BuffFunction::BuffOverrideInventoryAccessInput,
                "buff function was not copied");
        Require(observation.FunctionNameIndex == kBuffOverrideInventoryAccessInputNameIndex,
                "buff function name index was not copied");
        Require(observation.OuterNameIndex == kPrimalBuffNameIndex, "buff outer name index was not copied");
        Require(observation.BoolCount == 2, "BuffOverrideInventoryAccessInput bool count mismatch");
        RequireBool(observation,
                    0,
                    BuffReflection::BuffField::BInputPressed,
                    true,
                    "bInputPressed copied value mismatch");
        RequireBool(observation,
                    1,
                    BuffReflection::BuffField::ReturnValue,
                    false,
                    "ReturnValue copied value mismatch");
    }

    void TestBuildsSupportedCopiedBuffShapes()
    {
        uint8_t falseValue = 0;
        uint8_t trueValue = 1;

        {
            BuffReflection::BuffInvocation invocation;
            invocation.Function = BuffReflection::BuffFunction::AllowPostProcessEffect;
            invocation.FunctionNameIndex = kAllowPostProcessEffectNameIndex;
            invocation.OuterNameIndex = kPrimalBuffNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(BuffReflection::BuffField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  kBoolPropertyClassNameIndex,
                                                  kBoolPropertyClassObjectIndex,
                                                  kBoolReturnPropertyFlags,
                                                  0x00,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &trueValue,
                                                  sizeof(trueValue)));

            CopiedBuffObservation observation;
            Require(TryBuildCopiedBuffObservation(invocation, observation),
                    "AllowPostProcessEffect copied observation was rejected");
            Require(observation.BoolCount == 1, "AllowPostProcessEffect bool count mismatch");
            RequireBool(observation,
                        0,
                        BuffReflection::BuffField::ReturnValue,
                        true,
                        "AllowPostProcessEffect ReturnValue mismatch");
        }

        {
            BuffReflection::BuffInvocation invocation = MakeBuffOverrideInvocation(trueValue, falseValue);

            CopiedBuffObservation observation;
            Require(TryBuildCopiedBuffObservation(invocation, observation),
                    "BuffOverrideInventoryAccessInput copied observation was rejected");
            Require(observation.BoolCount == 2, "BuffOverrideInventoryAccessInput bool count mismatch");
            RequireBool(observation,
                        0,
                        BuffReflection::BuffField::BInputPressed,
                        true,
                        "BuffOverrideInventoryAccessInput bInputPressed mismatch");
            RequireBool(observation,
                        1,
                        BuffReflection::BuffField::ReturnValue,
                        false,
                        "BuffOverrideInventoryAccessInput ReturnValue mismatch");
        }

        {
            BuffReflection::BuffInvocation invocation;
            invocation.Function = BuffReflection::BuffFunction::BPCustomAllowAddBuff;
            invocation.FunctionNameIndex = kBPCustomAllowAddBuffNameIndex;
            invocation.OuterNameIndex = kPrimalBuffNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(BuffReflection::BuffField::ForCharacter,
                                                  kForCharacterNameIndex,
                                                  kObjectPropertyClassNameIndex,
                                                  kObjectPropertyClassObjectIndex,
                                                  kObjectInputPropertyFlags,
                                                  0x00,
                                                  sizeof(uint64_t),
                                                  false));
            invocation.Fields.push_back(MakeField(BuffReflection::BuffField::DamageCauser,
                                                  kDamageCauserNameIndex,
                                                  kObjectPropertyClassNameIndex,
                                                  kObjectPropertyClassObjectIndex,
                                                  kObjectInputPropertyFlags,
                                                  0x08,
                                                  sizeof(uint64_t),
                                                  false));
            invocation.Fields.push_back(MakeField(BuffReflection::BuffField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  kBoolPropertyClassNameIndex,
                                                  kBoolPropertyClassObjectIndex,
                                                  kBoolReturnPropertyFlags,
                                                  0x10,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &trueValue,
                                                  sizeof(trueValue)));

            CopiedBuffObservation observation;
            Require(TryBuildCopiedBuffObservation(invocation, observation),
                    "BPCustomAllowAddBuff copied observation was rejected");
            Require(observation.BoolCount == 1, "BPCustomAllowAddBuff bool count mismatch");
            RequireBool(observation,
                        0,
                        BuffReflection::BuffField::ReturnValue,
                        true,
                        "BPCustomAllowAddBuff ReturnValue mismatch");
        }

        {
            BuffReflection::BuffInvocation invocation;
            invocation.Function = BuffReflection::BuffFunction::BPOnBuffLifetimeUpdated;
            invocation.FunctionNameIndex = kBPOnBuffLifetimeUpdatedNameIndex;
            invocation.OuterNameIndex = kPrimalBuffNameIndex;
            invocation.HasParameterRanges = false;

            CopiedBuffObservation observation;
            Require(TryBuildCopiedBuffObservation(invocation, observation),
                    "zero-bool buff observation was rejected");
            Require(observation.BoolCount == 0, "zero-bool buff observation copied bools");
        }
    }

    void TestRejectsForgedOrNonCanonicalCopiedDataAndClearsOutput()
    {
        uint8_t validValue = 1;
        uint8_t invalidValue = 2;

        {
            BuffReflection::BuffInvocation invocation = MakeBuffOverrideInvocation(validValue, validValue);
            invocation.Fields[0].Range = {&validValue, sizeof(validValue)};
            RequireRejected(invocation, "recognition-only object range was accepted");
        }

        {
            BuffReflection::BuffInvocation invocation = MakeBuffOverrideInvocation(invalidValue, validValue);
            RequireRejected(invocation, "non-canonical bInputPressed was accepted");
        }

        {
            BuffReflection::BuffInvocation invocation = MakeBuffOverrideInvocation(validValue, invalidValue);
            RequireRejected(invocation, "non-canonical ReturnValue was accepted");
        }

        {
            BuffReflection::BuffInvocation invocation = MakeBuffOverrideInvocation(validValue, validValue);
            invocation.Fields[1].PropertyNameIndex = kReturnValueNameIndex;
            RequireRejected(invocation, "wrong copied bool metadata was accepted");
        }
    }

    void TestRecognizesAllRuntimeBuffFixtureShapes()
    {
        struct Case
        {
            int32_t NameIndex = -1;
            void (*Build)(BuffFixture&) = nullptr;
            size_t ExpectedBoolCount = 0;
        };

        const std::array<Case, 6> cases{{
            {kAllowPostProcessEffectNameIndex,
             [](BuffFixture& fixture) { BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex); },
             1},
            {kBPOnBuffLifetimeUpdatedNameIndex, BuildZeroParam, 0},
            {kBPBuffPreventUploadingNameIndex,
             [](BuffFixture& fixture) { BuildBoolReturn(fixture, kBPBuffPreventUploadingNameIndex); },
             1},
            {kBPCustomAllowAddBuffNameIndex, BuildBPCustomAllowAddBuff, 1},
            {kBPPreventAddingOtherBuffNameIndex, BuildBPPreventAddingOtherBuff, 1},
            {kBuffOverrideInventoryAccessInputNameIndex, BuildBuffOverrideInventoryAccessInput, 2},
        }};

        for (const Case& item : cases)
        {
            BuffFixture fixture;
            item.Build(fixture);
            fixture.Params.fill(0);

            std::atomic<uint64_t> counter{0};
            uint64_t observationNumber = 0;
            Attempt attempt = TryObserveInvocation(
                EnabledGate(),
                item.NameIndex,
                fixture.Reader(),
                fixture.Function.data(),
                fixture.Params.data(),
                counter,
                1,
                observationNumber);

            Require(attempt.Status == AttemptStatus::Matched, "valid buff fixture was not matched");
            CopiedBuffObservation observation;
            Require(TryBuildCopiedBuffObservationForMatchedAttempt(attempt, observation),
                    "valid buff fixture did not build copied observation");
            Require(observation.BoolCount == item.ExpectedBoolCount, "valid buff fixture bool count mismatch");
        }
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationBudgetAndFilter();
    TestDisabledNonBuffAndZeroBudgetDoNotReadOrReserve();
    TestObserveContainsReaderExceptions();
    TestObserveMatchesAndBuildsCopiedObservation();
    TestBuildsSupportedCopiedBuffShapes();
    TestRejectsForgedOrNonCanonicalCopiedDataAndClearsOutput();
    TestRecognizesAllRuntimeBuffFixtureShapes();

    std::cout << "ProcessEventBuffReflectionTests passed\n";
    return 0;
}
