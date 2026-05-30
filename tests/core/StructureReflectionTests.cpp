#include "ue/StructureReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace
{
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kAllowStructureAccessNameIndex = 7541;
    constexpr int32_t kIsAllowedToDemolishNameIndex = 7574;
    constexpr int32_t kSetVariantNameIndex = 7605;
    constexpr int32_t kAllowToggleActivationNameIndex = 7620;
    constexpr int32_t kVerifyPinCodeNameIndex = 7636;
    constexpr int32_t kCanSeatNameIndex = 8481;
    constexpr int32_t kPrimalStructureNameIndex = 7539;
    constexpr int32_t kPrimalStructureItemContainerNameIndex = 7617;
    constexpr int32_t kPrimalStructureSeatingNameIndex = 8480;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kStrPropertyClassNameIndex = 13;
    constexpr int32_t kForPCNameIndex = 18805;
    constexpr int32_t kForCharacterNameIndex = 17726;
    constexpr int32_t kBForceNameIndex = 18793;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kVariantIndexNameIndex = 22292;
    constexpr int32_t kBForceSetNameIndex = 22388;
    constexpr int32_t kPinCodeNameIndex = 22699;

    struct Region
    {
        const uint8_t* Start = nullptr;
        size_t Size = 0;
    };

    struct ReaderContext
    {
        std::vector<Region> Regions;
    };

    bool RegionReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<ReaderContext*>(context);
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
        std::array<uint8_t, 0x40> StrPropertyClass{};
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
            Context.Regions.push_back({StrPropertyClass.data(), StrPropertyClass.size()});
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    ReadOptions Options()
    {
        return MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
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
        WriteObject(fixture.StrPropertyClass,
                    kStrPropertyClassNameIndex,
                    kStrPropertyClassNameIndex,
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
        WriteObject(fixture.Outer, outerNameIndex, outerNameIndex, nullptr, nullptr);
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

    void TestRecognizesVerifyPinCodeWithoutExposingPinCode()
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
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == StructureReflection::StructureFunction::VerifyPinCode,
                "VerifyPinCode kind mismatch");
        Require(invocation.Fields.size() == 2, "VerifyPinCode field count mismatch");
        Require(invocation.Fields[0].Field == StructureReflection::StructureField::PinCode,
                "PinCode field mismatch");
        Require(invocation.Fields[0].Sensitive, "PinCode should be marked sensitive");
        Require(!invocation.Fields[0].ExposesRange, "PinCode should not expose a borrowed range");
        Require(invocation.Fields[0].Range.Data == nullptr, "PinCode range data was exposed");
        Require(invocation.Fields[1].Field == StructureReflection::StructureField::ReturnValue,
                "ReturnValue field mismatch");
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x04,
                "ReturnValue range pointer mismatch");
        Require(invocation.Fields[1].Range.Size == 1, "ReturnValue range size mismatch");
    }

    void TestRecognizesStructureScalarShapes()
    {
        {
            StructureFixture fixture;
            BuildFunction(fixture,
                          kAllowToggleActivationNameIndex,
                          kPrimalStructureItemContainerNameIndex,
                          2,
                          0x09,
                          0x08,
                          ForPCReturnFields(fixture));

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == StructureReflection::StructureFunction::AllowToggleActivation,
                    "AllowToggleActivation kind mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr, "ForPC object range should not be exposed");
            Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                    "AllowToggleActivation return range mismatch");
        }
        {
            StructureFixture fixture;
            BuildSetVariant(fixture);

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == StructureReflection::StructureFunction::SetVariant,
                    "SetVariant kind mismatch");
            Require(invocation.Fields[0].Range.Data == fixture.Params.data(),
                    "VariantIndex range mismatch");
            Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x04,
                    "bForceSet range mismatch");
            Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x05,
                    "SetVariant return range mismatch");
        }
        {
            StructureFixture fixture;
            BuildCanSeat(fixture);

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == StructureReflection::StructureFunction::CanSeat,
                    "CanSeat kind mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr, "ForPC range should not be exposed");
            Require(invocation.Fields[1].Range.Data == nullptr, "forCharacter range should not be exposed");
            Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x10,
                    "bForce range mismatch");
            Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x11,
                    "CanSeat return range mismatch");
        }
    }

    void TestRecognizesAccessAndDemolishBaselines()
    {
        for (const auto [nameIndex, expected] : {
                 std::pair{kAllowStructureAccessNameIndex, StructureReflection::StructureFunction::AllowStructureAccess},
                 std::pair{kIsAllowedToDemolishNameIndex, StructureReflection::StructureFunction::IsAllowedToDemolish},
             })
        {
            StructureFixture fixture;
            BuildFunction(fixture,
                          nameIndex,
                          kPrimalStructureNameIndex,
                          2,
                          0x09,
                          0x08,
                          ForPCReturnFields(fixture));

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                nullptr,
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == expected, "access/demolish kind mismatch");
            Require(!invocation.HasParameterRanges, "null params should not expose ranges");
        }
    }

    void TestRejectsPartialNameCollisionByOuter()
    {
        StructureFixture fixture;
        BuildFunction(fixture,
                      kAllowStructureAccessNameIndex,
                      kPrimalStructureItemContainerNameIndex,
                      2,
                      0x09,
                      0x08,
                      ForPCReturnFields(fixture));

        StructureReflection::StructureInvocation invocation;
        ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "wrong outer was accepted");
    }

    void TestRejectsWrongShapeAndUnsupportedProperty()
    {
        {
            StructureFixture fixture;
            BuildVerifyPinCode(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x09});

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible, "wrong ParmsSize was accepted");
        }
        {
            StructureFixture fixture;
            BuildFunction(fixture,
                          kVerifyPinCodeNameIndex,
                          kPrimalStructureItemContainerNameIndex,
                          2,
                          0x11,
                          0x10,
                          {{
                              {kPinCodeNameIndex, 0x00, 0x10, fixture.StrPropertyClass.data()},
                              {kReturnValueNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data()},
                              {},
                              {},
                          }});

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible, "unsupported StrProperty was accepted");
        }
    }

    void TestRejectsPropertyMetadataDrift()
    {
        {
            StructureFixture fixture;
            BuildSetVariant(fixture);
            WriteAt(fixture.PropertyB, 0x30, int32_t{2});

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible, "wrong bForceSet ArrayDim was accepted");
        }
        {
            StructureFixture fixture;
            BuildSetVariant(fixture);
            WriteAt(fixture.PropertyB, 0x34, int32_t{2});

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible, "wrong bForceSet ElementSize was accepted");
        }
        {
            StructureFixture fixture;
            BuildVerifyPinCode(fixture);
            WriteObject(fixture.IntPropertyClass, kIntPropertyClassNameIndex, 99001, nullptr, nullptr);

            StructureReflection::StructureInvocation invocation;
            ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "wrong PinCode IntProperty class object index was accepted");
        }
    }

    void TestGateRejectsBeforeReading()
    {
        StructureFixture fixture;
        BuildVerifyPinCode(fixture);

        StructureReflection::StructureInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = StructureReflection::TryIdentifyStructureInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled structure reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = StructureReflection::TryIdentifyStructureInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported structure reflection was accepted");
    }

    void TestNonPinCopiedScalarFilterIsExact()
    {
        Require(StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::SetVariant),
                "SetVariant function was rejected by non-pin copied-scalar filter");
        Require(StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::AllowToggleActivation),
                "AllowToggleActivation function was rejected by non-pin copied-scalar filter");
        Require(StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::CanSeat),
                "CanSeat function was rejected by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::VerifyPinCode),
                "VerifyPinCode function was accepted by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::AllowStructureAccess),
                "AllowStructureAccess function was accepted by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunction(
                    StructureReflection::StructureFunction::IsAllowedToDemolish),
                "IsAllowedToDemolish function was accepted by non-pin copied-scalar filter");

        Require(!StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kAllowStructureAccessNameIndex),
                "AllowStructureAccess FName was accepted by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kIsAllowedToDemolishNameIndex),
                "IsAllowedToDemolish FName was accepted by non-pin copied-scalar filter");
        Require(StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kSetVariantNameIndex),
                "SetVariant FName was rejected by non-pin copied-scalar filter");
        Require(StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kAllowToggleActivationNameIndex),
                "AllowToggleActivation FName was rejected by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kVerifyPinCodeNameIndex),
                "VerifyPinCode FName was accepted by non-pin copied-scalar filter");
        Require(StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(kCanSeatNameIndex),
                "CanSeat FName was rejected by non-pin copied-scalar filter");
        Require(!StructureReflection::IsNonPinCopiedScalarFunctionNameIndex(42),
                "unrelated FName was accepted by non-pin copied-scalar filter");
    }
}

int main()
{
    TestRecognizesVerifyPinCodeWithoutExposingPinCode();
    TestRecognizesStructureScalarShapes();
    TestRecognizesAccessAndDemolishBaselines();
    TestRejectsPartialNameCollisionByOuter();
    TestRejectsWrongShapeAndUnsupportedProperty();
    TestRejectsPropertyMetadataDrift();
    TestGateRejectsBeforeReading();
    TestNonPinCopiedScalarFilterIsExact();

    std::cout << "StructureReflectionTests passed\n";
    return 0;
}
