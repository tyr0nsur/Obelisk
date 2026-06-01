#include "hooks/ProcessEventDinoReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>

namespace
{
    using namespace Obelisk::Hooks::ProcessEventDinoReflection;
    using namespace Obelisk::UE::DinoReflection;

    constexpr int32_t kAddPassengerNameIndex = 8267;
    constexpr int32_t kAllowCarryCharacterNameIndex = 8269;
    constexpr int32_t kPrimalDinoCharacterNameIndex = 8265;
    constexpr int32_t kACharacterNameIndex = 4044;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBSkipLineTraceNameIndex = 25580;
    constexpr int32_t kBAllowFlyersAndWaterDinosNameIndex = 25581;
    constexpr int32_t kBForcePassengerNameIndex = 25582;
    constexpr int32_t kPassengerSeatIndexNameIndex = 25583;
    constexpr int32_t kCanCarryPawnNameIndex = 25584;

    static_assert(std::is_standard_layout_v<DinoScalarValue>,
                  "copied dino scalar values must keep a simple internal layout");
    static_assert(std::is_trivially_copyable_v<DinoScalarValue>,
                  "copied dino scalar values must remain byte-copyable");
    static_assert(std::is_standard_layout_v<CopiedDinoScalarObservation>,
                  "copied dino observations must keep a simple internal layout");
    static_assert(std::is_trivially_copyable_v<CopiedDinoScalarObservation>,
                  "copied dino observations must remain byte-copyable");

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    DinoFieldRange MakeField(DinoField field,
                             int32_t propertyNameIndex,
                             int32_t offset,
                             size_t size,
                             bool exposesRange,
                             const uint8_t* data = nullptr,
                             size_t rangeSize = 0)
    {
        DinoFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = propertyNameIndex;
        value.Offset = offset;
        value.Size = size;
        value.ExposesRange = exposesRange;
        if (exposesRange)
            value.Range = {data, rangeSize};
        return value;
    }

    DinoInvocation MakeValidAddPassengerInvocation(std::array<uint8_t, 0x10>& params)
    {
        DinoInvocation invocation;
        invocation.Function = DinoFunction::AddPassenger;
        invocation.FunctionNameIndex = kAddPassengerNameIndex;
        invocation.OuterNameIndex = kPrimalDinoCharacterNameIndex;
        invocation.HasParameterRanges = true;
        invocation.ParameterData = params.data();
        invocation.ParameterSize = params.size();
        invocation.Fields.push_back(MakeField(DinoField::ACharacter,
                                              kACharacterNameIndex,
                                              0x00,
                                              sizeof(uint64_t),
                                              false));
        invocation.Fields.push_back(MakeField(DinoField::PassengerSeatIndex,
                                              kPassengerSeatIndexNameIndex,
                                              0x08,
                                              sizeof(int32_t),
                                              true,
                                              params.data() + 0x08,
                                              sizeof(int32_t)));
        invocation.Fields.push_back(MakeField(DinoField::BForcePassenger,
                                              kBForcePassengerNameIndex,
                                              0x0c,
                                              sizeof(uint8_t),
                                              true,
                                              params.data() + 0x0c,
                                              sizeof(uint8_t)));
        invocation.Fields.push_back(MakeField(DinoField::BAllowFlyersAndWaterDinos,
                                              kBAllowFlyersAndWaterDinosNameIndex,
                                              0x0d,
                                              sizeof(uint8_t),
                                              true,
                                              params.data() + 0x0d,
                                              sizeof(uint8_t)));
        invocation.Fields.push_back(MakeField(DinoField::BSkipLineTrace,
                                              kBSkipLineTraceNameIndex,
                                              0x0e,
                                              sizeof(uint8_t),
                                              true,
                                              params.data() + 0x0e,
                                              sizeof(uint8_t)));
        invocation.Fields.push_back(MakeField(DinoField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x0f,
                                              sizeof(uint8_t),
                                              false));
        return invocation;
    }

    DinoInvocation MakeAllowCarryCharacterInvocation(std::array<uint8_t, 0x09>& params)
    {
        DinoInvocation invocation;
        invocation.Function = DinoFunction::AllowCarryCharacter;
        invocation.FunctionNameIndex = kAllowCarryCharacterNameIndex;
        invocation.OuterNameIndex = kPrimalDinoCharacterNameIndex;
        invocation.HasParameterRanges = true;
        invocation.ParameterData = params.data();
        invocation.ParameterSize = params.size();
        invocation.Fields.push_back(MakeField(DinoField::CanCarryPawn,
                                              kCanCarryPawnNameIndex,
                                              0x00,
                                              sizeof(uint64_t),
                                              false));
        invocation.Fields.push_back(MakeField(DinoField::ReturnValue,
                                              kReturnValueNameIndex,
                                              0x08,
                                              sizeof(uint8_t),
                                              true,
                                              params.data() + 0x08,
                                              sizeof(uint8_t)));
        return invocation;
    }

    void Poison(CopiedDinoScalarObservation& observation)
    {
        observation.ScalarCount = 1;
        observation.ScalarStorage[0] = {
            .Field = DinoScalarField::BSkipLineTrace,
            .Type = DinoScalarType::Bool,
            .BoolValue = true,
            .Int32Value = 77,
        };
    }

    void RequireRejected(const DinoInvocation& invocation, const char* message)
    {
        CopiedDinoScalarObservation observation;
        Poison(observation);
        Require(!TryBuildCopiedDinoScalarObservation(invocation, observation), message);
        Require(observation.ScalarCount == 0, "rejected copied dino observation left scalar payload");
    }

    std::array<uint8_t, 0x10> MakeCanonicalAddPassengerParams()
    {
        std::array<uint8_t, 0x10> params{};
        const int32_t seatIndex = 1;
        std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
        params[0x0c] = 1;
        params[0x0d] = 0;
        params[0x0e] = 1;
        params[0x0f] = 0;
        return params;
    }

    template <typename Mutator>
    void RequireRejectedAddPassengerMutation(Mutator mutator, const char* message)
    {
        std::array<uint8_t, 0x10> params = MakeCanonicalAddPassengerParams();
        DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
        mutator(invocation);
        RequireRejected(invocation, message);
    }

    void RequireScalar(const CopiedDinoScalarObservation& observation,
                       size_t index,
                       DinoScalarField field,
                       DinoScalarType type,
                       bool boolValue,
                       int32_t int32Value,
                       const char* message)
    {
        Require(index < observation.ScalarCount, message);
        Require(observation.ScalarStorage[index].Field == field, message);
        Require(observation.ScalarStorage[index].Type == type, message);
        Require(observation.ScalarStorage[index].BoolValue == boolValue, message);
        Require(observation.ScalarStorage[index].Int32Value == int32Value, message);
    }

    void TestBuildsAddPassengerCopiedScalars()
    {
        std::array<uint8_t, 0x10> params{};
        const int32_t seatIndex = -3;
        std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
        params[0x0c] = 1;
        params[0x0d] = 0;
        params[0x0e] = 1;
        params[0x0f] = 9;

        DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
        CopiedDinoScalarObservation observation;
        Require(TryBuildCopiedDinoScalarObservation(invocation, observation),
                "AddPassenger copied dino observation was rejected");
        Require(observation.Function == DinoFunction::AddPassenger, "AddPassenger function was not copied");
        Require(observation.ScalarCount == 4, "AddPassenger copied wrong scalar count");

        RequireScalar(observation,
                      0,
                      DinoScalarField::PassengerSeatIndex,
                      DinoScalarType::Int32,
                      false,
                      seatIndex,
                      "PassengerSeatIndex scalar mismatch");
        RequireScalar(observation,
                      1,
                      DinoScalarField::BForcePassenger,
                      DinoScalarType::Bool,
                      true,
                      0,
                      "bForcePassenger scalar mismatch");
        RequireScalar(observation,
                      2,
                      DinoScalarField::BAllowFlyersAndWaterDinos,
                      DinoScalarType::Bool,
                      false,
                      0,
                      "bAllowFlyersAndWaterDinos scalar mismatch");
        RequireScalar(observation,
                      3,
                      DinoScalarField::BSkipLineTrace,
                      DinoScalarType::Bool,
                      true,
                      0,
                      "bSkipLineTrace scalar mismatch");
    }

    void TestBuildDoesNotMutateParams()
    {
        std::array<uint8_t, 0x10> params{};
        const int32_t seatIndex = 2;
        std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
        params[0x0c] = 0;
        params[0x0d] = 1;
        params[0x0e] = 0;
        params[0x0f] = 1;
        const std::array<uint8_t, 0x10> before = params;

        CopiedDinoScalarObservation observation;
        Require(TryBuildCopiedDinoScalarObservation(MakeValidAddPassengerInvocation(params), observation),
                "AddPassenger copied dino observation was rejected");
        Require(params == before, "copied dino observation mutated parameter bytes");
    }

    void TestRejectsNonAddPassengerAndMetadataOnly()
    {
        {
            std::array<uint8_t, 0x09> params{};
            params[0x08] = 1;
            RequireRejected(MakeAllowCarryCharacterInvocation(params),
                            "AllowCarryCharacter produced a pre-call dino scalar observation");
        }
        {
            std::array<uint8_t, 0x10> params{};
            DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
            invocation.HasParameterRanges = false;
            for (DinoFieldRange& field : invocation.Fields)
                field.Range = {};
            RequireRejected(invocation, "metadata-only AddPassenger produced copied dino scalars");
        }
    }

    void TestRequiresExactAddPassengerInvocationShape()
    {
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.FunctionNameIndex = kAddPassengerNameIndex + 1; },
            "wrong AddPassenger FunctionNameIndex built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.OuterNameIndex = kPrimalDinoCharacterNameIndex + 1; },
            "wrong AddPassenger OuterNameIndex built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                DinoFieldRange swapped = invocation.Fields[1];
                invocation.Fields[1] = invocation.Fields[2];
                invocation.Fields[2] = swapped;
            },
            "reordered AddPassenger fields built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[1].PropertyNameIndex = kPassengerSeatIndexNameIndex + 1; },
            "wrong PassengerSeatIndex name index built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[1].Offset = 0x04; },
            "wrong PassengerSeatIndex offset built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[1].Size = sizeof(int16_t); },
            "wrong PassengerSeatIndex size built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[1].ExposesRange = false; },
            "PassengerSeatIndex without exposed range built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields.Count = 5; },
            "truncated AddPassenger field chain built copied scalars");
    }

    void TestRejectsExcludedDinoFieldsAsCopiedScalars()
    {
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                invocation.Fields[1].Field = DinoField::ACharacter;
                invocation.Fields[1].PropertyNameIndex = kACharacterNameIndex;
            },
            "ACharacter copied-scalar slot built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                invocation.Fields[1].Field = DinoField::ReturnValue;
                invocation.Fields[1].PropertyNameIndex = kReturnValueNameIndex;
            },
            "ReturnValue copied-scalar slot built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                invocation.Fields[1].Field = DinoField::CanCarryPawn;
                invocation.Fields[1].PropertyNameIndex = kCanCarryPawnNameIndex;
            },
            "CanCarryPawn copied-scalar slot built copied scalars");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                static const uint8_t returnValue = 0;
                invocation.Fields.clear();
                invocation.Fields.push_back(MakeField(DinoField::ReturnValue,
                                                      kReturnValueNameIndex,
                                                      0x0f,
                                                      sizeof(uint8_t),
                                                      true,
                                                      &returnValue,
                                                      sizeof(uint8_t)));
            },
            "ReturnValue-only AddPassenger shape built copied scalars");
    }

    void TestRejectsBadCopiedScalarRanges()
    {
        {
            std::array<uint8_t, 0x10> params{};
            const int32_t seatIndex = 1;
            std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
            params[0x0c] = 2;
            params[0x0d] = 0;
            params[0x0e] = 1;
            DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
            RequireRejected(invocation, "non-canonical AddPassenger bool was copied");
        }
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[3].Range.Data = nullptr; },
            "null AddPassenger bool range was copied");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.Fields[4].Range.Size = 0; },
            "zero-sized AddPassenger bool range was copied");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.ParameterData = nullptr; },
            "AddPassenger range without parameter provenance was copied");
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) { invocation.ParameterSize = 0x0c; },
            "AddPassenger range beyond parameter provenance was copied");
        {
            std::array<uint8_t, 0x10> params = MakeCanonicalAddPassengerParams();
            DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
            static const int32_t forgedSeatIndex = 1;
            invocation.Fields[1].Range = {
                reinterpret_cast<const uint8_t*>(&forgedSeatIndex),
                sizeof(forgedSeatIndex),
            };
            RequireRejected(invocation, "forged PassengerSeatIndex range provenance was copied");
        }
        {
            std::array<uint8_t, 0x10> params{};
            params[0x0c] = 1;
            params[0x0d] = 0;
            params[0x0e] = 1;
            DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
            invocation.Fields[1].Range.Size = sizeof(int16_t);
            RequireRejected(invocation, "short PassengerSeatIndex range was copied");
        }
        {
            std::array<uint8_t, 0x10> params{};
            const int32_t seatIndex = 1;
            std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
            params[0x0c] = 1;
            params[0x0d] = 0;
            params[0x0e] = 1;
            DinoInvocation invocation = MakeValidAddPassengerInvocation(params);
            invocation.Fields[0].ExposesRange = true;
            invocation.Fields[0].Range = {params.data(), sizeof(uint64_t)};
            RequireRejected(invocation, "forged ACharacter copied range was accepted");
        }
        RequireRejectedAddPassengerMutation(
            [](DinoInvocation& invocation) {
                static const uint8_t returnValue = 0;
                invocation.Fields[5].Range = {&returnValue, sizeof(uint8_t)};
            },
            "malformed ReturnValue range was accepted");
    }

    void TestReturnValueStaysOutOfPreCallPayload()
    {
        std::array<uint8_t, 0x10> params{};
        const int32_t seatIndex = 4;
        std::memcpy(params.data() + 0x08, &seatIndex, sizeof(seatIndex));
        params[0x0c] = 1;
        params[0x0d] = 1;
        params[0x0e] = 0;
        params[0x0f] = 255;

        CopiedDinoScalarObservation observation;
        Require(TryBuildCopiedDinoScalarObservation(MakeValidAddPassengerInvocation(params), observation),
                "AddPassenger with ignored ReturnValue was rejected");
        Require(observation.ScalarCount == 4, "ReturnValue changed copied scalar count");
        for (size_t index = 0; index < observation.ScalarCount; ++index)
        {
            Require(observation.ScalarStorage[index].Field != DinoScalarField::PassengerSeatIndex ||
                        observation.ScalarStorage[index].Int32Value == seatIndex,
                    "ReturnValue contaminated copied scalar payload");
        }
    }

    void TestCopiedDinoObservationShape()
    {
        Require(std::is_standard_layout_v<DinoScalarValue>,
                "dino scalar value must remain standard-layout");
        Require(std::is_trivially_copyable_v<DinoScalarValue>,
                "dino scalar value must remain trivially copyable");
        Require(std::is_standard_layout_v<CopiedDinoScalarObservation>,
                "copied dino observation must remain standard-layout");
        Require(std::is_trivially_copyable_v<CopiedDinoScalarObservation>,
                "copied dino observation must remain trivially copyable");
        Require(std::tuple_size<decltype(CopiedDinoScalarObservation{}.ScalarStorage)>::value == 4,
                "copied dino scalar storage changed unexpectedly");
    }
}

int main()
{
    try
    {
        TestCopiedDinoObservationShape();
        TestBuildsAddPassengerCopiedScalars();
        TestBuildDoesNotMutateParams();
        TestRejectsNonAddPassengerAndMetadataOnly();
        TestRequiresExactAddPassengerInvocationShape();
        TestRejectsExcludedDinoFieldsAsCopiedScalars();
        TestRejectsBadCopiedScalarRanges();
        TestReturnValueStaysOutOfPreCallPayload();
    }
    catch (const std::exception& ex)
    {
        std::cerr << "ProcessEventDinoReflectionTests failed: " << ex.what() << "\n";
        return 1;
    }

    std::cout << "ProcessEventDinoReflectionTests passed\n";
    return 0;
}
