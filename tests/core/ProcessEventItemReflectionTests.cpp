#include "hooks/ProcessEventItemReflection.h"

#include <atomic>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <type_traits>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventItemReflection;
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kAllowEquipItemNameIndex = 6235;
    constexpr int32_t kCanRepairNameIndex = 6250;
    constexpr int32_t kCraftBlueprintNameIndex = 6257;
    constexpr int32_t kUseItemOntoItemNameIndex = 6346;
    constexpr int32_t kPrimalItemNameIndex = 6231;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBIgnoreInventoryRequirementNameIndex = 18617;
    constexpr int32_t kToInventoryNameIndex = 18795;
    constexpr int32_t kDestinationItemNameIndex = 19285;
    constexpr int32_t kAdditionalDataNameIndex = 19290;
    constexpr int32_t kBConsumeResourcesNameIndex = 19293;

    static_assert(std::is_standard_layout_v<ItemBoolObservation>,
                  "copied item bool observations must keep a simple C-compatible layout");
    static_assert(std::is_trivially_copyable_v<ItemBoolObservation>,
                  "copied item bool observations must remain byte-copyable");
    static_assert(std::is_standard_layout_v<CopiedItemObservation>,
                  "copied item observations must keep a simple C-compatible layout");
    static_assert(std::is_trivially_copyable_v<CopiedItemObservation>,
                  "copied item observations must remain byte-copyable");

    struct ReaderContext
    {
        int Calls = 0;
    };

    bool CountingReader(const void*, size_t, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
        ++reader->Calls;
        return false;
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("expected item reflection reader exception");
    }

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    Gate EnabledGate()
    {
        return EvaluateGate("1", true, true, true, kSupportedShooterGameServerSha256.data());
    }

    Obelisk::UE::ItemReflection::ItemFieldRange MakeField(Obelisk::UE::ItemReflection::ItemField field,
                                                          int32_t propertyNameIndex,
                                                          int32_t offset,
                                                          size_t size,
                                                          bool exposesRange,
                                                          const uint8_t* data = nullptr,
                                                          size_t rangeSize = 0)
    {
        Obelisk::UE::ItemReflection::ItemFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = propertyNameIndex;
        value.Offset = offset;
        value.Size = size;
        value.ExposesRange = exposesRange;
        if (exposesRange)
            value.Range = {data, rangeSize};
        return value;
    }

    void RequireRejected(const Obelisk::UE::ItemReflection::ItemInvocation& invocation,
                         const char* message)
    {
        CopiedItemObservation observation;
        observation.BoolCount = 1;
        observation.BoolStorage[0].Field = Obelisk::UE::ItemReflection::ItemField::BConsumeResources;
        observation.BoolStorage[0].Value = true;

        Require(!TryBuildCopiedItemObservation(invocation, observation), message);
        Require(observation.BoolCount == 0, "rejected copied item observation left bool payload");
    }

    void RequireAttemptRejected(const Attempt& attempt, const char* message)
    {
        CopiedItemObservation observation;
        observation.BoolCount = 1;
        observation.BoolStorage[0].Field = Obelisk::UE::ItemReflection::ItemField::ReturnValue;
        observation.BoolStorage[0].Value = true;

        Require(!TryBuildCopiedItemReturnObservationForMatchedAttempt(attempt, observation), message);
        Require(observation.BoolCount == 0, "rejected matched-attempt item observation left bool payload");
    }

    void RequireBool(const CopiedItemObservation& observation,
                     size_t index,
                     Obelisk::UE::ItemReflection::ItemField field,
                     bool value,
                     const char* message)
    {
        Require(index < observation.BoolCount, message);
        Require(observation.BoolStorage[index].Field == field, message);
        Require(observation.BoolStorage[index].Value == value, message);
    }

    void RequireReturnOnlyPayload(const CopiedItemObservation& observation,
                                  bool expectedReturnValue,
                                  const char* message)
    {
        Require(observation.BoolCount == 1, message);
        RequireBool(observation,
                    0,
                    Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                    expectedReturnValue,
                    message);
        for (size_t index = 0; index < observation.BoolCount; ++index)
        {
            Require(observation.BoolStorage[index].Field !=
                        Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
                    "bIgnoreInventoryRequirement entered copied item payload");
            Require(observation.BoolStorage[index].Field !=
                        Obelisk::UE::ItemReflection::ItemField::BConsumeResources,
                    "bConsumeResources entered copied item payload");
        }
    }

    Obelisk::UE::ItemReflection::ItemInvocation MakeValidAllowEquipItemInvocation(uint8_t& returnValue)
    {
        Obelisk::UE::ItemReflection::ItemInvocation invocation;
        invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem;
        invocation.FunctionNameIndex = kAllowEquipItemNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ToInventory,
                                              kToInventoryNameIndex,
                                              0x00,
                                              sizeof(uint64_t),
                                              false));
        invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x08,
                                              sizeof(uint8_t),
                                              true,
                                              &returnValue,
                                              sizeof(returnValue)));
        return invocation;
    }

    Obelisk::UE::ItemReflection::ItemInvocation MakeValidCanRepairInvocation(uint8_t& ignoreInventoryRequirement,
                                                                             uint8_t& returnValue)
    {
        Obelisk::UE::ItemReflection::ItemInvocation invocation;
        invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
        invocation.FunctionNameIndex = kCanRepairNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
            kBIgnoreInventoryRequirementNameIndex,
            0x00,
            sizeof(uint8_t),
            true,
            &ignoreInventoryRequirement,
            sizeof(ignoreInventoryRequirement)));
        invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x01,
                                              sizeof(uint8_t),
                                              true,
                                              &returnValue,
                                              sizeof(returnValue)));
        return invocation;
    }

    void TestGateEvaluation()
    {
        Require(EvaluateGate(nullptr, true, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::Disabled,
                "missing item env should disable gate");
        Require(EvaluateGate("0", true, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::Disabled,
                "non-one item env should disable gate");
        Require(EvaluateGate("1", false, true, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingObserverDebugProfile,
                "missing observer profile was not reported");
        Require(EvaluateGate("1", true, false, true, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingObserverDebugWindow,
                "missing observer window was not reported");
        Require(EvaluateGate("1", true, true, false, kSupportedShooterGameServerSha256.data()).Status ==
                    GateStatus::MissingInstanceMarker,
                "missing item marker was not reported");
        Require(EvaluateGate("1", true, true, true, nullptr).Status == GateStatus::MissingBinarySha256,
                "missing binary hash was not reported");
        Require(EvaluateGate("1", true, true, true, "bad-sha").Status == GateStatus::UnsupportedBinarySha256,
                "unsupported binary hash was not reported");

        Gate gate = EnabledGate();
        Require(gate.Enabled(), "valid item gate did not enable");
        Require(gate.BinarySha256 == kSupportedShooterGameServerSha256, "item gate did not retain binary hash");
    }

    void TestObservationBudgetAndFilter()
    {
        Require(IsReflectedItemNameIndex(kAllowEquipItemNameIndex), "AllowEquipItem name should be recognized");
        Require(IsReflectedItemNameIndex(kCanRepairNameIndex), "CanRepair name should be recognized");
        Require(IsReflectedItemNameIndex(kCraftBlueprintNameIndex), "CraftBlueprint name should be recognized");
        Require(IsReflectedItemNameIndex(kUseItemOntoItemNameIndex), "UseItemOntoItem name should be recognized");
        Require(!IsReflectedItemNameIndex(9999), "unknown item name should not be recognized");

        Require(!ShouldAttemptObservation(0), "zero item observation limit should disable observation");
        Require(ShouldAttemptObservation(1), "non-zero item observation limit should enable observation");
        Require(ShouldAttemptNameObservation(kCanRepairNameIndex, 1),
                "matching item name and budget should pass filter");
        Require(!ShouldAttemptNameObservation(kCanRepairNameIndex, 0),
                "zero item budget should block matching name");
        Require(!ShouldAttemptNameObservation(9999, 1), "unknown item name should not pass filter");

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Require(HasObservationBudgetRemaining(counter, 1), "initial item budget should remain");
        Require(TryReserveObservationBudget(counter, 1, observationNumber), "failed to reserve item budget");
        Require(observationNumber == 1, "wrong item observation number");
        Require(!HasObservationBudgetRemaining(counter, 1), "exhausted item budget reported remaining");
        Require(!TryReserveObservationBudget(counter, 1, observationNumber), "reserved exhausted item budget");
        Require(observationNumber == 0, "exhausted item budget left observation number set");
        Require(ShouldLogObservation(1, 1), "first item observation should log");
        Require(!ShouldLogObservation(2, 1), "over-limit item observation should not log");
    }

    void TestDisabledAndNonItemDoNotRead()
    {
        ReaderContext context;
        MemoryReader reader{CountingReader, &context};

        Attempt disabled = TryIdentifyInvocation({}, kCanRepairNameIndex, reader, nullptr, nullptr);
        Require(disabled.Status == AttemptStatus::Disabled, "disabled item gate attempted read");
        Require(context.Calls == 0, "disabled item gate read memory");

        Attempt nonItem = TryIdentifyInvocation(EnabledGate(), 9999, reader, nullptr, nullptr);
        Require(nonItem.Status == AttemptStatus::NonItemFunction, "non-item name was not rejected before read");
        Require(context.Calls == 0, "non-item name read memory");
    }

    void TestObserveDisabledNonItemAndZeroBudgetDoNotReadOrReserve()
    {
        ReaderContext context;
        MemoryReader reader{CountingReader, &context};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;

        Attempt disabled = TryObserveInvocation(
            {},
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);
        Require(disabled.Status == AttemptStatus::Disabled, "disabled item observation attempted read");
        Require(observationNumber == 0, "disabled item observation left observation number set");
        Require(counter.load() == 0, "disabled item observation reserved budget");
        Require(context.Calls == 0, "disabled item observation read memory");

        observationNumber = 99;
        Attempt nonItem = TryObserveInvocation(
            EnabledGate(),
            9999,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);
        Require(nonItem.Status == AttemptStatus::NonItemFunction,
                "non-item observation was not rejected before budget");
        Require(observationNumber == 0, "non-item observation left observation number set");
        Require(counter.load() == 0, "non-item observation reserved budget");
        Require(context.Calls == 0, "non-item observation read memory");

        observationNumber = 99;
        Attempt zeroBudget = TryObserveInvocation(
            EnabledGate(),
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            0,
            observationNumber);
        Require(zeroBudget.Status == AttemptStatus::BudgetExhausted,
                "zero-budget item observation did not fail closed before read");
        Require(observationNumber == 0, "zero-budget item observation left observation number set");
        Require(counter.load() == 0, "zero-budget item observation reserved budget");
        Require(context.Calls == 0, "zero-budget item observation read memory");
    }

    void TestIdentifyContainsReaderExceptions()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Attempt attempt = TryIdentifyInvocation(
            EnabledGate(),
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000));
        Require(attempt.Status == AttemptStatus::Rejected, "throwing item reader escaped bridge");
        Require(attempt.Result.Status == ReadStatus::Implausible, "throwing item reader used wrong status");
    }

    void TestBuildsCopiedItemObservations()
    {
        uint8_t falseValue = 0;
        uint8_t trueValue = 1;

        {
            Obelisk::UE::ItemReflection::ItemInvocation invocation;
            invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem;
            invocation.FunctionNameIndex = kAllowEquipItemNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ToInventory,
                                                  kToInventoryNameIndex,
                                                  0x00,
                                                  sizeof(uint64_t),
                                                  false));
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  0x08,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &trueValue,
                                                  sizeof(trueValue)));

            CopiedItemObservation observation;
            Require(TryBuildCopiedItemObservation(invocation, observation),
                    "AllowEquipItem copied observation was rejected");
            Require(observation.Function == Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem,
                    "AllowEquipItem function was not copied");
            Require(observation.FunctionNameIndex == kAllowEquipItemNameIndex,
                    "AllowEquipItem function index was not copied");
            Require(observation.OuterNameIndex == kPrimalItemNameIndex,
                    "AllowEquipItem outer index was not copied");
            RequireReturnOnlyPayload(observation, true, "AllowEquipItem return-only payload mismatch");
        }

        {
            Obelisk::UE::ItemReflection::ItemInvocation invocation;
            invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
            invocation.FunctionNameIndex = kCanRepairNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(
                Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
                kBIgnoreInventoryRequirementNameIndex,
                0x00,
                sizeof(uint8_t),
                true,
                &trueValue,
                sizeof(trueValue)));
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  0x01,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &falseValue,
                                                  sizeof(falseValue)));

            CopiedItemObservation observation;
            Require(TryBuildCopiedItemObservation(invocation, observation),
                    "CanRepair copied observation was rejected");
            RequireReturnOnlyPayload(observation, false, "CanRepair return-only payload mismatch");
        }

        {
            Obelisk::UE::ItemReflection::ItemInvocation invocation;
            invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CraftBlueprint;
            invocation.FunctionNameIndex = kCraftBlueprintNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::BConsumeResources,
                                                  kBConsumeResourcesNameIndex,
                                                  0x00,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &falseValue,
                                                  sizeof(falseValue)));

            CopiedItemObservation observation;
            Require(!TryBuildCopiedItemObservation(invocation, observation),
                    "CraftBlueprint produced a public-compatible copied item observation");
        }

        {
            Obelisk::UE::ItemReflection::ItemInvocation invocation;
            invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::UseItemOntoItem;
            invocation.FunctionNameIndex = kUseItemOntoItemNameIndex;
            invocation.OuterNameIndex = kPrimalItemNameIndex;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::DestinationItem,
                                                  kDestinationItemNameIndex,
                                                  0x00,
                                                  sizeof(uint64_t),
                                                  false));
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::AdditionalData,
                                                  kAdditionalDataNameIndex,
                                                  0x08,
                                                  sizeof(int32_t),
                                                  false));
            invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  0x0c,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &trueValue,
                                                  sizeof(trueValue)));

            CopiedItemObservation observation;
            Require(TryBuildCopiedItemObservation(invocation, observation),
                    "UseItemOntoItem copied observation was rejected");
            RequireReturnOnlyPayload(observation, true, "UseItemOntoItem return-only payload mismatch");
        }
    }

    void TestCopiedItemObservationAbiShape()
    {
        Require(std::is_standard_layout_v<ItemBoolObservation>,
                "item bool observation must remain standard-layout");
        Require(std::is_trivially_copyable_v<ItemBoolObservation>,
                "item bool observation must remain trivially copyable");
        Require(std::is_standard_layout_v<CopiedItemObservation>,
                "copied item observation must remain standard-layout");
        Require(std::is_trivially_copyable_v<CopiedItemObservation>,
                "copied item observation must remain trivially copyable");
        Require(std::tuple_size<decltype(CopiedItemObservation{}.BoolStorage)>::value == 2,
                "copied item observation bool storage changed unexpectedly");
    }

    void TestBuildDoesNotMutateItemParams()
    {
        std::array<uint8_t, 16> params{};
        params[0x00] = 1;
        params[0x01] = 0;
        const std::array<uint8_t, 16> before = params;

        Obelisk::UE::ItemReflection::ItemInvocation invocation;
        invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
        invocation.FunctionNameIndex = kCanRepairNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
            kBIgnoreInventoryRequirementNameIndex,
            0x00,
            sizeof(uint8_t),
            true,
            params.data() + 0x00,
            sizeof(uint8_t)));
        invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x01,
                                              sizeof(uint8_t),
                                              true,
                                              params.data() + 0x01,
                                              sizeof(uint8_t)));

        CopiedItemObservation observation;
        Require(TryBuildCopiedItemObservation(invocation, observation),
                "CanRepair copied item observation was rejected");
        RequireReturnOnlyPayload(observation, false, "CanRepair return-only payload mismatch");
        Require(params == before, "copied item observation mutated parameter bytes");
    }

    void TestBuildsCopiedReturnObservationOnlyForMatchedAttempts()
    {
        uint8_t returnValue = 1;
        Obelisk::UE::ItemReflection::ItemInvocation returnBearing =
            MakeValidAllowEquipItemInvocation(returnValue);

        Attempt matched;
        matched.Status = AttemptStatus::Matched;
        matched.Invocation = returnBearing;

        CopiedItemObservation observation;
        Require(TryBuildCopiedItemReturnObservationForMatchedAttempt(matched, observation),
                "matched return-bearing item attempt did not build copied output");
        RequireReturnOnlyPayload(observation, true, "matched return-bearing item payload mismatch");

        std::array<AttemptStatus, 4> nonMatchedStatuses{{
            AttemptStatus::Disabled,
            AttemptStatus::BudgetExhausted,
            AttemptStatus::NonItemFunction,
            AttemptStatus::Rejected,
        }};
        for (AttemptStatus status : nonMatchedStatuses)
        {
            Attempt nonMatched;
            nonMatched.Status = status;
            nonMatched.Invocation = returnBearing;
            RequireAttemptRejected(nonMatched, "non-matched item attempt built copied output");
        }

        uint8_t consumeResources = 1;
        Attempt matchedWithoutReturn;
        matchedWithoutReturn.Status = AttemptStatus::Matched;
        matchedWithoutReturn.Invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CraftBlueprint;
        matchedWithoutReturn.Invocation.FunctionNameIndex = kCraftBlueprintNameIndex;
        matchedWithoutReturn.Invocation.OuterNameIndex = kPrimalItemNameIndex;
        matchedWithoutReturn.Invocation.HasParameterRanges = true;
        matchedWithoutReturn.Invocation.Fields.push_back(
            MakeField(Obelisk::UE::ItemReflection::ItemField::BConsumeResources,
                      kBConsumeResourcesNameIndex,
                      0x00,
                      sizeof(uint8_t),
                      true,
                      &consumeResources,
                      sizeof(consumeResources)));
        RequireAttemptRejected(matchedWithoutReturn,
                               "matched item attempt without ReturnValue built copied output");
    }

    void TestRejectsMalformedReturnOnlyShapes()
    {
        uint8_t returnValue = 1;
        uint8_t ignoredRequirement = 1;
        uint8_t consumeResources = 1;
        uint8_t oversizedReturn[2] = {1, 0};

        Obelisk::UE::ItemReflection::ItemInvocation validCanRepair;
        validCanRepair.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
        validCanRepair.FunctionNameIndex = kCanRepairNameIndex;
        validCanRepair.OuterNameIndex = kPrimalItemNameIndex;
        validCanRepair.HasParameterRanges = true;
        validCanRepair.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
            kBIgnoreInventoryRequirementNameIndex,
            0x00,
            sizeof(uint8_t),
            true,
            &ignoredRequirement,
            sizeof(ignoredRequirement)));
        validCanRepair.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                  kReturnValueNameIndex,
                                                  0x01,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &returnValue,
                                                  sizeof(returnValue)));

        CopiedItemObservation observation;
        Require(TryBuildCopiedItemObservation(validCanRepair, observation),
                "valid CanRepair fixture should build before malformed variants");
        RequireReturnOnlyPayload(observation,
                                 true,
                                 "CanRepair copied bIgnoreInventoryRequirement instead of ReturnValue");

        Obelisk::UE::ItemReflection::ItemInvocation wrongFunctionName = validCanRepair;
        wrongFunctionName.FunctionNameIndex = kAllowEquipItemNameIndex;
        RequireRejected(wrongFunctionName, "wrong item function name built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation wrongOuterName = validCanRepair;
        wrongOuterName.OuterNameIndex = 9999;
        RequireRejected(wrongOuterName, "wrong item outer name built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation reordered = validCanRepair;
        const Obelisk::UE::ItemReflection::ItemFieldRange firstField = reordered.Fields[0];
        reordered.Fields[0] = reordered.Fields[1];
        reordered.Fields[1] = firstField;
        Require(!TryBuildCopiedItemObservation(reordered, observation),
                "reordered CanRepair fields built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation wrongName = validCanRepair;
        wrongName.Fields[1].PropertyNameIndex = kBIgnoreInventoryRequirementNameIndex;
        Require(!TryBuildCopiedItemObservation(wrongName, observation),
                "wrong ReturnValue property name built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation wrongOffset = validCanRepair;
        wrongOffset.Fields[1].Offset = 0x02;
        Require(!TryBuildCopiedItemObservation(wrongOffset, observation),
                "wrong ReturnValue offset built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation wrongSize = validCanRepair;
        wrongSize.Fields[1].Size = 2;
        wrongSize.Fields[1].Range = {oversizedReturn, sizeof(oversizedReturn)};
        Require(!TryBuildCopiedItemObservation(wrongSize, observation),
                "wrong ReturnValue size built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation zeroRange = validCanRepair;
        zeroRange.Fields[1].Range = {&returnValue, 0};
        Require(!TryBuildCopiedItemObservation(zeroRange, observation),
                "zero-sized ReturnValue range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation nullRange = validCanRepair;
        nullRange.Fields[1].Range = {nullptr, sizeof(uint8_t)};
        Require(!TryBuildCopiedItemObservation(nullRange, observation),
                "null ReturnValue range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation noReturnRange = validCanRepair;
        noReturnRange.Fields[1].ExposesRange = false;
        noReturnRange.Fields[1].Range = {};
        Require(!TryBuildCopiedItemObservation(noReturnRange, observation),
                "ReturnValue without exposed range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation missingReturn;
        missingReturn.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
        missingReturn.FunctionNameIndex = kCanRepairNameIndex;
        missingReturn.OuterNameIndex = kPrimalItemNameIndex;
        missingReturn.HasParameterRanges = true;
        missingReturn.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
            kBIgnoreInventoryRequirementNameIndex,
            0x00,
            sizeof(uint8_t),
            true,
            &ignoredRequirement,
            sizeof(ignoredRequirement)));
        Require(!TryBuildCopiedItemObservation(missingReturn, observation),
                "CanRepair without ReturnValue built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation craftBlueprint;
        craftBlueprint.Function = Obelisk::UE::ItemReflection::ItemFunction::CraftBlueprint;
        craftBlueprint.FunctionNameIndex = kCraftBlueprintNameIndex;
        craftBlueprint.OuterNameIndex = kPrimalItemNameIndex;
        craftBlueprint.HasParameterRanges = true;
        craftBlueprint.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::BConsumeResources,
                                                  kBConsumeResourcesNameIndex,
                                                  0x00,
                                                  sizeof(uint8_t),
                                                  true,
                                                  &consumeResources,
                                                  sizeof(consumeResources)));
        RequireRejected(craftBlueprint, "CraftBlueprint bConsumeResources built copied item observation");
    }

    void TestRejectsNonCanonicalBoolBytes()
    {
        uint8_t invalidReturnValue = 2;
        Obelisk::UE::ItemReflection::ItemInvocation invalidReturn =
            MakeValidAllowEquipItemInvocation(invalidReturnValue);
        RequireRejected(invalidReturn, "ReturnValue byte greater than one built copied item observation");

        uint8_t invalidIgnoredRequirement = 2;
        uint8_t validReturnValue = 1;
        Obelisk::UE::ItemReflection::ItemInvocation invalidInput =
            MakeValidCanRepairInvocation(invalidIgnoredRequirement, validReturnValue);
        RequireRejected(invalidInput,
                        "bIgnoreInventoryRequirement byte greater than one built copied item observation");

        Attempt matchedInvalidReturn;
        matchedInvalidReturn.Status = AttemptStatus::Matched;
        matchedInvalidReturn.Invocation = invalidReturn;
        RequireAttemptRejected(matchedInvalidReturn,
                               "matched item attempt with non-canonical ReturnValue built copied output");
    }

    void TestRejectsPartialCanRepairShape()
    {
        uint8_t returnValue = 1;
        Obelisk::UE::ItemReflection::ItemInvocation invocation;
        invocation.Function = Obelisk::UE::ItemReflection::ItemFunction::CanRepair;
        invocation.FunctionNameIndex = kCanRepairNameIndex;
        invocation.OuterNameIndex = kPrimalItemNameIndex;
        invocation.HasParameterRanges = true;
        invocation.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x01,
                                              sizeof(uint8_t),
                                              true,
                                              &returnValue,
                                              sizeof(returnValue)));

        CopiedItemObservation observation;
        Require(!TryBuildCopiedItemObservation(invocation, observation),
                "CanRepair partial ReturnValue-only shape bypassed exact metadata validation");
    }

    void TestRejectsMissingOrForbiddenRanges()
    {
        uint64_t inventory = 0x1111111122222222ULL;
        int32_t additionalData = 0x33333333;
        uint8_t returnValue = 1;

        Obelisk::UE::ItemReflection::ItemInvocation noRanges;
        noRanges.Function = Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem;
        noRanges.FunctionNameIndex = kAllowEquipItemNameIndex;
        noRanges.OuterNameIndex = kPrimalItemNameIndex;
        noRanges.HasParameterRanges = false;
        noRanges.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ToInventory,
                                            kToInventoryNameIndex,
                                            0x00,
                                            sizeof(uint64_t),
                                            false));
        noRanges.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                            kReturnValueNameIndex,
                                            0x08,
                                            sizeof(uint8_t),
                                            true,
                                            &returnValue,
                                            sizeof(returnValue)));

        CopiedItemObservation observation;
        Require(!TryBuildCopiedItemObservation(noRanges, observation),
                "item observation built without parameter-range ownership");

        Obelisk::UE::ItemReflection::ItemInvocation forgedInventoryRange = noRanges;
        forgedInventoryRange.HasParameterRanges = true;
        forgedInventoryRange.Fields[0] = MakeField(Obelisk::UE::ItemReflection::ItemField::ToInventory,
                                                   kToInventoryNameIndex,
                                                   0x00,
                                                   sizeof(uint64_t),
                                                   true,
                                                   reinterpret_cast<const uint8_t*>(&inventory),
                                                   sizeof(inventory));
        Require(!TryBuildCopiedItemObservation(forgedInventoryRange, observation),
                "forged toInventory range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation forgedDestinationItem;
        forgedDestinationItem.Function = Obelisk::UE::ItemReflection::ItemFunction::UseItemOntoItem;
        forgedDestinationItem.FunctionNameIndex = kUseItemOntoItemNameIndex;
        forgedDestinationItem.OuterNameIndex = kPrimalItemNameIndex;
        forgedDestinationItem.HasParameterRanges = true;
        forgedDestinationItem.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::DestinationItem,
            kDestinationItemNameIndex,
            0x00,
            sizeof(uint64_t),
            true,
            reinterpret_cast<const uint8_t*>(&inventory),
            sizeof(inventory)));
        forgedDestinationItem.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::AdditionalData,
                                                         kAdditionalDataNameIndex,
                                                         0x08,
                                                         sizeof(int32_t),
                                                         false));
        forgedDestinationItem.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                         kReturnValueNameIndex,
                                                         0x0c,
                                                         sizeof(uint8_t),
                                                         true,
                                                         &returnValue,
                                                         sizeof(returnValue)));
        Require(!TryBuildCopiedItemObservation(forgedDestinationItem, observation),
                "forged DestinationItem range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation forgedAdditionalData;
        forgedAdditionalData.Function = Obelisk::UE::ItemReflection::ItemFunction::UseItemOntoItem;
        forgedAdditionalData.FunctionNameIndex = kUseItemOntoItemNameIndex;
        forgedAdditionalData.OuterNameIndex = kPrimalItemNameIndex;
        forgedAdditionalData.HasParameterRanges = true;
        forgedAdditionalData.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::DestinationItem,
                                                        kDestinationItemNameIndex,
                                                        0x00,
                                                        sizeof(uint64_t),
                                                        false));
        forgedAdditionalData.Fields.push_back(MakeField(
            Obelisk::UE::ItemReflection::ItemField::AdditionalData,
            kAdditionalDataNameIndex,
            0x08,
            sizeof(int32_t),
            true,
            reinterpret_cast<const uint8_t*>(&additionalData),
            sizeof(additionalData)));
        forgedAdditionalData.Fields.push_back(MakeField(Obelisk::UE::ItemReflection::ItemField::ReturnValue,
                                                        kReturnValueNameIndex,
                                                        0x0c,
                                                        sizeof(uint8_t),
                                                        true,
                                                        &returnValue,
                                                        sizeof(returnValue)));
        Require(!TryBuildCopiedItemObservation(forgedAdditionalData, observation),
                "forged AdditionalData range built copied item observation");

        Obelisk::UE::ItemReflection::ItemInvocation nullForbiddenRange = forgedDestinationItem;
        nullForbiddenRange.Fields[0].Range = {nullptr, sizeof(uint64_t)};
        Require(!TryBuildCopiedItemObservation(nullForbiddenRange, observation),
                "null-data forbidden DestinationItem range built copied item observation");
    }

    void TestObserveReservesBudgetBeforeRead()
    {
        ReaderContext context;
        MemoryReader reader{CountingReader, &context};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;

        Attempt first = TryObserveInvocation(
            EnabledGate(),
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            nullptr,
            counter,
            1,
            observationNumber);
        Require(first.Status == AttemptStatus::Rejected, "first item observation should reach recognizer");
        Require(observationNumber == 1, "first item observation did not reserve budget");

        context.Calls = 0;
        Attempt second = TryObserveInvocation(
            EnabledGate(),
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            nullptr,
            counter,
            1,
            observationNumber);
        Require(second.Status == AttemptStatus::BudgetExhausted, "second item observation did not exhaust budget");
        Require(observationNumber == 0, "exhausted item observation left observation number set");
        Require(context.Calls == 0, "exhausted item observation read memory");
    }

    void TestObserveReaderExceptionFailsClosedAfterBudgetReservation()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;

        Attempt attempt = TryObserveInvocation(
            EnabledGate(),
            kCanRepairNameIndex,
            reader,
            reinterpret_cast<void*>(0x1000),
            reinterpret_cast<void*>(0x2000),
            counter,
            1,
            observationNumber);

        Require(attempt.Status == AttemptStatus::Rejected,
                "throwing item reader did not fail closed through hook observation");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "throwing item reader used wrong hook observation status");
        Require(counter.load() == 1,
                "throwing item reader did not consume bounded observation budget after FName prefilter");
        Require(observationNumber == 1,
                "throwing item reader did not preserve the reserved observation number");
    }
}

int main()
{
    TestGateEvaluation();
    TestObservationBudgetAndFilter();
    TestDisabledAndNonItemDoNotRead();
    TestObserveDisabledNonItemAndZeroBudgetDoNotReadOrReserve();
    TestIdentifyContainsReaderExceptions();
    TestBuildsCopiedItemObservations();
    TestCopiedItemObservationAbiShape();
    TestBuildDoesNotMutateItemParams();
    TestBuildsCopiedReturnObservationOnlyForMatchedAttempts();
    TestRejectsMalformedReturnOnlyShapes();
    TestRejectsNonCanonicalBoolBytes();
    TestRejectsPartialCanRepairShape();
    TestRejectsMissingOrForbiddenRanges();
    TestObserveReservesBudgetBeforeRead();
    TestObserveReaderExceptionFailsClosedAfterBudgetReservation();

    std::cout << "ProcessEventItemReflectionTests passed\n";
    return 0;
}
