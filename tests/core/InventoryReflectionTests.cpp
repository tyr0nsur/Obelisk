#include "ue/InventoryReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
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
                     const void* outer,
                     int32_t nameNumber = 0)
    {
        const void* vtable = reinterpret_cast<const void*>(0x10000);
        const int32_t flags = 1;
        const FNameValue name{nameIndex, nameNumber};

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

    ReadOptions Options()
    {
        return MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
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

    void RequireFieldMetadata(const InventoryReflection::InventoryFieldRange& field,
                              InventoryReflection::InventoryField expectedField,
                              int32_t expectedNameIndex,
                              int32_t expectedOffset,
                              size_t expectedSize,
                              bool expectedExposesRange)
    {
        Require(field.Field == expectedField, "inventory field kind mismatch");
        Require(field.PropertyNameIndex == expectedNameIndex, "inventory field FName mismatch");
        Require(field.Offset == expectedOffset, "inventory field offset mismatch");
        Require(field.Size == expectedSize, "inventory field size mismatch");
        Require(field.ExposesRange == expectedExposesRange, "inventory field exposure mismatch");
    }

    void TestRecognizesCanUseScalarShape()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);
        fixture.Params[0] = 1;
        fixture.Params[1] = 0;

        InventoryReflection::InventoryInvocation invocation;
        ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == InventoryReflection::InventoryFunction::CanUse, "CanUse kind mismatch");
        Require(invocation.Fields.size() == 2, "CanUse field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             InventoryReflection::InventoryField::BIgnoreCooldown,
                             kBIgnoreCooldownNameIndex,
                             0x00,
                             0x01,
                             true);
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(), "bIgnoreCooldown range mismatch");
        Require(invocation.Fields[0].Range.Size == 0x01, "bIgnoreCooldown range size mismatch");
        RequireFieldMetadata(invocation.Fields[1],
                             InventoryReflection::InventoryField::ReturnValue,
                             kReturnValueNameIndex,
                             0x01,
                             0x01,
                             true);
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 1, "ReturnValue range mismatch");
        Require(invocation.Fields[1].Range.Size == 0x01, "ReturnValue range size mismatch");
    }

    void TestRecognizesAllowRemoteAddWithoutObjectRanges()
    {
        InventoryFixture fixture;
        BuildAllowRemoteAdd(fixture);
        fixture.Params[0x10] = 1;
        fixture.Params[0x11] = 1;

        InventoryReflection::InventoryInvocation invocation;
        ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == InventoryReflection::InventoryFunction::AllowRemoteAddToInventory,
                "AllowRemoteAddToInventory kind mismatch");
        Require(invocation.Fields.size() == 4, "AllowRemoteAddToInventory field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             InventoryReflection::InventoryField::InventoryComponent,
                             kInvCompNameIndex,
                             0x00,
                             0x08,
                             false);
        Require(invocation.Fields[0].Range.Data == nullptr, "invComp range should not be exposed");
        RequireFieldMetadata(invocation.Fields[1],
                             InventoryReflection::InventoryField::ByPC,
                             kByPCNameIndex,
                             0x08,
                             0x08,
                             false);
        Require(invocation.Fields[1].Range.Data == nullptr, "ByPC range should not be exposed");
        RequireFieldMetadata(invocation.Fields[2],
                             InventoryReflection::InventoryField::BRequestedByPlayer,
                             kBRequestedByPlayerNameIndex,
                             0x10,
                             0x01,
                             true);
        Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x10,
                "bRequestedByPlayer range mismatch");
        Require(invocation.Fields[2].Range.Size == 0x01, "bRequestedByPlayer range size mismatch");
        RequireFieldMetadata(invocation.Fields[3],
                             InventoryReflection::InventoryField::ReturnValue,
                             kReturnValueNameIndex,
                             0x11,
                             0x01,
                             true);
        Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x11,
                "ReturnValue range mismatch");
        Require(invocation.Fields[3].Range.Size == 0x01, "ReturnValue range size mismatch");
    }

    void TestRejectsWrongOuterAndNameNumber()
    {
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.Outer, 9999, 9999, nullptr, nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong outer was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.Outer, kPrimalItemNameIndex, kPrimalItemNameIndex, nullptr, nullptr, 1);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered outer FName was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.Function,
                        kCanUseNameIndex,
                        kCanUseNameIndex,
                        reinterpret_cast<const void*>(0x20000),
                        fixture.Outer.data(),
                        1);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered function FName was accepted");
        }
    }

    void TestRejectsWrongShape()
    {
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{kCanUseFunctionFlags ^ 0x400});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong FunctionFlags were accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteAt(fixture.Function, 0x96, uint16_t{3});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong NumParms was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x03});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong ParmsSize was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kReturnValueNameIndex,
                          0x00,
                          0x01);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong first property FName was accepted");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kInvCompNameIndex,
                          0x00,
                          0x01);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong object property class was accepted");
        }
    }

    void TestGateRejectsBeforeReading()
    {
        InventoryFixture fixture;
        BuildCanUse(fixture);

        InventoryReflection::InventoryInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled inventory reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported inventory reflection was accepted");
    }
}

int main()
{
    TestRecognizesCanUseScalarShape();
    TestRecognizesAllowRemoteAddWithoutObjectRanges();
    TestRejectsWrongOuterAndNameNumber();
    TestRejectsWrongShape();
    TestGateRejectsBeforeReading();

    std::cout << "InventoryReflectionTests passed\n";
    return 0;
}
