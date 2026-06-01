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
    constexpr int32_t kServerRequestInventoryUseItemNameIndex = 2651;
    constexpr int32_t kServerRequestInventoryUseItemWithActorNameIndex = 2652;
    constexpr int32_t kPrimalItemNameIndex = 6231;
    constexpr int32_t kPrimalItemObjectIndex = 17;
    constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
    constexpr int32_t kShooterPlayerControllerObjectIndex = 50;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kStructPropertyClassNameIndex = 10;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kStructPropertyClassObjectIndex = 548;
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
    constexpr uint32_t kInventoryActionFunctionFlags = 0x00220cc0;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint64_t kRemoteAddInventoryComponentPropertyFlags = 0x1044080280;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kIntInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kStructInputPropertyFlags = 0x1040000280;

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

    struct InventoryFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> IntPropertyClass{};
        std::array<uint8_t, 0x40> StructPropertyClass{};
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
            Context.Regions.push_back({IntPropertyClass.data(), IntPropertyClass.size()});
            Context.Regions.push_back({StructPropertyClass.data(), StructPropertyClass.size()});
            Context.Regions.push_back({FunctionClass.data(), FunctionClass.size()});
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
                    kBoolPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.IntPropertyClass,
                    kIntPropertyClassNameIndex,
                    kIntPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.StructPropertyClass,
                    kStructPropertyClassNameIndex,
                    kStructPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(InventoryFixture& fixture,
                       int32_t functionNameIndex,
                       int32_t outerNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 4>& fields,
                       int32_t outerObjectIndex = kPrimalItemObjectIndex)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, outerNameIndex, outerObjectIndex, nullptr, nullptr);
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
                      kPrimalItemNameIndex,
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

    void BuildServerRequestInventoryUseItem(InventoryFixture& fixture)
    {
        BuildFunction(fixture,
                      kServerRequestInventoryUseItemNameIndex,
                      kShooterPlayerControllerNameIndex,
                      kInventoryActionFunctionFlags,
                      2,
                      0x10,
                      0xffff,
                      {{
                          {kInventoryCompNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kRemoteAddInventoryComponentPropertyFlags},
                          {kItemIdNameIndex,
                           0x08,
                           0x08,
                           fixture.StructPropertyClass.data(),
                           kStructInputPropertyFlags},
                          {},
                          {},
                      }},
                      kShooterPlayerControllerObjectIndex);
    }

    void BuildServerRequestInventoryUseItemWithActor(InventoryFixture& fixture)
    {
        BuildFunction(fixture,
                      kServerRequestInventoryUseItemWithActorNameIndex,
                      kShooterPlayerControllerNameIndex,
                      kInventoryActionFunctionFlags,
                      4,
                      0x1c,
                      0xffff,
                      {{
                          {kAnActorNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kInventoryCompNameIndex,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kRemoteAddInventoryComponentPropertyFlags},
                          {kItemID1NameIndex,
                           0x10,
                           0x08,
                           fixture.StructPropertyClass.data(),
                           kStructInputPropertyFlags},
                          {kAdditionalDataNameIndex,
                           0x18,
                           0x04,
                           fixture.IntPropertyClass.data(),
                           kIntInputPropertyFlags},
                      }},
                      kShooterPlayerControllerObjectIndex);
    }

    void BuildAllowRemoteAdd(InventoryFixture& fixture)
    {
        BuildFunction(fixture,
                      kAllowRemoteAddToInventoryNameIndex,
                      kPrimalItemNameIndex,
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

    void RequireFieldMetadata(const InventoryReflection::InventoryFieldRange& field,
                              InventoryReflection::InventoryField expectedField,
                              int32_t expectedNameIndex,
                              int32_t expectedClassNameIndex,
                              int32_t expectedClassObjectIndex,
                              uint64_t expectedPropertyFlags,
                              int32_t expectedOffset,
                              size_t expectedSize,
                              bool expectedExposesRange)
    {
        Require(field.Field == expectedField, "inventory field kind mismatch");
        Require(field.PropertyNameIndex == expectedNameIndex, "inventory field FName mismatch");
        Require(field.PropertyClassNameIndex == expectedClassNameIndex, "inventory field class FName mismatch");
        Require(field.PropertyClassObjectIndex == expectedClassObjectIndex,
                "inventory field class object index mismatch");
        Require(field.PropertyFlags == expectedPropertyFlags, "inventory field property flags mismatch");
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
                             kBoolPropertyClassNameIndex,
                             kBoolPropertyClassObjectIndex,
                             kBoolInputPropertyFlags,
                             0x00,
                             0x01,
                             true);
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(), "bIgnoreCooldown range mismatch");
        Require(invocation.Fields[0].Range.Size == 0x01, "bIgnoreCooldown range size mismatch");
        RequireFieldMetadata(invocation.Fields[1],
                             InventoryReflection::InventoryField::ReturnValue,
                             kReturnValueNameIndex,
                             kBoolPropertyClassNameIndex,
                             kBoolPropertyClassObjectIndex,
                             kBoolReturnPropertyFlags,
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
                             kObjectPropertyClassNameIndex,
                             kObjectPropertyClassObjectIndex,
                             kRemoteAddInventoryComponentPropertyFlags,
                             0x00,
                             0x08,
                             false);
        Require(invocation.Fields[0].Range.Data == nullptr, "invComp range should not be exposed");
        RequireFieldMetadata(invocation.Fields[1],
                             InventoryReflection::InventoryField::ByPC,
                             kByPCNameIndex,
                             kObjectPropertyClassNameIndex,
                             kObjectPropertyClassObjectIndex,
                             kObjectInputPropertyFlags,
                             0x08,
                             0x08,
                             false);
        Require(invocation.Fields[1].Range.Data == nullptr, "ByPC range should not be exposed");
        RequireFieldMetadata(invocation.Fields[2],
                             InventoryReflection::InventoryField::BRequestedByPlayer,
                             kBRequestedByPlayerNameIndex,
                             kBoolPropertyClassNameIndex,
                             kBoolPropertyClassObjectIndex,
                             kBoolInputPropertyFlags,
                             0x10,
                             0x01,
                             true);
        Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x10,
                "bRequestedByPlayer range mismatch");
        Require(invocation.Fields[2].Range.Size == 0x01, "bRequestedByPlayer range size mismatch");
        RequireFieldMetadata(invocation.Fields[3],
                             InventoryReflection::InventoryField::ReturnValue,
                             kReturnValueNameIndex,
                             kBoolPropertyClassNameIndex,
                             kBoolPropertyClassObjectIndex,
                             kBoolReturnPropertyFlags,
                             0x11,
                             0x01,
                             true);
        Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x11,
                "ReturnValue range mismatch");
        Require(invocation.Fields[3].Range.Size == 0x01, "ReturnValue range size mismatch");
    }

    void TestRecognizesInventoryActionsAsMetadataOnly()
    {
        {
            InventoryFixture fixture;
            BuildServerRequestInventoryUseItem(fixture);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                reinterpret_cast<const void*>(0x20000),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == InventoryReflection::InventoryFunction::ServerRequestInventoryUseItem,
                    "ServerRequestInventoryUseItem kind mismatch");
            Require(invocation.Fields.size() == 2, "ServerRequestInventoryUseItem field count mismatch");
            Require(invocation.HasParameterRanges,
                    "ServerRequestInventoryUseItem should record params availability without exposing ranges");
            RequireFieldMetadata(invocation.Fields[0],
                                 InventoryReflection::InventoryField::InventoryComponent,
                                 kInventoryCompNameIndex,
                                 kObjectPropertyClassNameIndex,
                                 kObjectPropertyClassObjectIndex,
                                 kRemoteAddInventoryComponentPropertyFlags,
                                 0x00,
                                 0x08,
                                 false);
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "ServerRequestInventoryUseItem InventoryComp range should stay hidden");
            RequireFieldMetadata(invocation.Fields[1],
                                 InventoryReflection::InventoryField::RedactedItemId,
                                 kItemIdNameIndex,
                                 kStructPropertyClassNameIndex,
                                 kStructPropertyClassObjectIndex,
                                 kStructInputPropertyFlags,
                                 0x08,
                                 0x08,
                                 false);
            Require(invocation.Fields[1].Range.Data == nullptr,
                    "ServerRequestInventoryUseItem ItemId range should stay hidden");
        }
        {
            InventoryFixture fixture;
            BuildServerRequestInventoryUseItemWithActor(fixture);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                reinterpret_cast<const void*>(0x20000),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function ==
                        InventoryReflection::InventoryFunction::ServerRequestInventoryUseItemWithActor,
                    "ServerRequestInventoryUseItemWithActor kind mismatch");
            Require(invocation.Fields.size() == 4,
                    "ServerRequestInventoryUseItemWithActor field count mismatch");
            RequireFieldMetadata(invocation.Fields[0],
                                 InventoryReflection::InventoryField::Actor,
                                 kAnActorNameIndex,
                                 kObjectPropertyClassNameIndex,
                                 kObjectPropertyClassObjectIndex,
                                 kObjectInputPropertyFlags,
                                 0x00,
                                 0x08,
                                 false);
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "ServerRequestInventoryUseItemWithActor actor range should stay hidden");
            RequireFieldMetadata(invocation.Fields[1],
                                 InventoryReflection::InventoryField::InventoryComponent,
                                 kInventoryCompNameIndex,
                                 kObjectPropertyClassNameIndex,
                                 kObjectPropertyClassObjectIndex,
                                 kRemoteAddInventoryComponentPropertyFlags,
                                 0x08,
                                 0x08,
                                 false);
            Require(invocation.Fields[1].Range.Data == nullptr,
                    "ServerRequestInventoryUseItemWithActor InventoryComp range should stay hidden");
            RequireFieldMetadata(invocation.Fields[2],
                                 InventoryReflection::InventoryField::RedactedItemId1,
                                 kItemID1NameIndex,
                                 kStructPropertyClassNameIndex,
                                 kStructPropertyClassObjectIndex,
                                 kStructInputPropertyFlags,
                                 0x10,
                                 0x08,
                                 false);
            Require(invocation.Fields[2].Range.Data == nullptr,
                    "ServerRequestInventoryUseItemWithActor ItemID1 range should stay hidden");
            RequireFieldMetadata(invocation.Fields[3],
                                 InventoryReflection::InventoryField::AdditionalData,
                                 kAdditionalDataNameIndex,
                                 kIntPropertyClassNameIndex,
                                 kIntPropertyClassObjectIndex,
                                 kIntInputPropertyFlags,
                                 0x18,
                                 0x04,
                                 false);
            Require(invocation.Fields[3].Range.Data == nullptr,
                    "ServerRequestInventoryUseItemWithActor AdditionalData range should stay hidden");
        }
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
                        fixture.FunctionClass.data(),
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

    void TestRejectsWrongFunctionClass()
    {
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.Function,
                        kCanUseNameIndex,
                        kCanUseNameIndex,
                        nullptr,
                        fixture.Outer.data());

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "null function class was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.Function,
                        kCanUseNameIndex,
                        kCanUseNameIndex,
                        reinterpret_cast<const void*>(0x20000),
                        fixture.Outer.data());

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Unreadable, "unreadable function class was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.FunctionClass, 9999, kFunctionClassObjectIndex, nullptr, nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong function class FName was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.FunctionClass,
                        kFunctionClassNameIndex,
                        kFunctionClassObjectIndex,
                        nullptr,
                        nullptr,
                        1);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered Function class FName was accepted");
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
            BuildAllowRemoteAdd(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{kAllowRemoteAddToInventoryFunctionFlags ^ 0x400});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong AllowRemoteAddToInventory FunctionFlags were accepted");
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
            WriteAt(fixture.Function, 0x9a, uint16_t{0x00});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong ReturnValueOffset was accepted");
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
                          0x01,
                          kBoolInputPropertyFlags);

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
            WriteProperty(fixture.PropertyC,
                          fixture.PropertyD.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kReturnValueNameIndex,
                          0x10,
                          0x01,
                          kBoolReturnPropertyFlags);
            WriteProperty(fixture.PropertyD,
                          nullptr,
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kBRequestedByPlayerNameIndex,
                          0x11,
                          0x01,
                          kBoolInputPropertyFlags);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "reordered AllowRemoteAddToInventory bool fields were accepted");
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
                          0x01,
                          kBoolInputPropertyFlags);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong object property class was accepted");
        }
        {
            InventoryFixture fixture;
            BuildServerRequestInventoryUseItem(fixture);
            WriteObject(fixture.Outer,
                        kShooterPlayerControllerNameIndex,
                        kPrimalItemObjectIndex,
                        nullptr,
                        nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong inventory action outer object index was accepted");
        }
        {
            InventoryFixture fixture;
            BuildServerRequestInventoryUseItemWithActor(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x20});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong inventory action ParmsSize was accepted");
        }
        {
            InventoryFixture fixture;
            BuildServerRequestInventoryUseItemWithActor(fixture);
            WriteProperty(fixture.PropertyD,
                          nullptr,
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kAdditionalDataNameIndex,
                          0x18,
                          0x01,
                          kBoolInputPropertyFlags);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong inventory action AdditionalData property class was accepted");
        }
    }

    void TestRejectsWrongPropertyMetadata()
    {
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteAt(fixture.PropertyA, 0x38, uint64_t{kBoolInputPropertyFlags ^ 0x400});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong CanUse bool property flags were accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.BoolPropertyClass,
                        kObjectPropertyClassNameIndex,
                        kBoolPropertyClassObjectIndex,
                        nullptr,
                        nullptr);

            InventoryReflection::InventoryInvocation invocation;
            invocation.FunctionNameIndex = 123;
            invocation.OuterNameIndex = 456;
            invocation.HasParameterRanges = true;
            invocation.Fields.push_back({});
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong BoolProperty class FName was accepted");
            Require(invocation.FunctionNameIndex == -1, "rejected BoolProperty FName left stale function name");
            Require(invocation.OuterNameIndex == -1, "rejected BoolProperty FName left stale outer name");
            Require(!invocation.HasParameterRanges, "rejected BoolProperty FName left stale range state");
            Require(invocation.Fields.empty(), "rejected BoolProperty FName left stale fields");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteAt(fixture.PropertyB, 0x38, uint64_t{kBoolInputPropertyFlags});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong CanUse return property flags were accepted");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            WriteAt(fixture.PropertyA, 0x38, uint64_t{kObjectInputPropertyFlags});

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong AllowRemoteAddToInventory invComp property flags were accepted");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            WriteObject(fixture.ObjectPropertyClass,
                        kBoolPropertyClassNameIndex,
                        kObjectPropertyClassObjectIndex,
                        nullptr,
                        nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong ObjectProperty class FName was accepted for AllowRemoteAddToInventory");
            Require(invocation.FunctionNameIndex == -1, "rejected ObjectProperty FName left stale function name");
            Require(invocation.Fields.empty(), "rejected ObjectProperty FName left stale fields");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            WriteObject(fixture.ObjectPropertyClass,
                        kObjectPropertyClassNameIndex,
                        kBoolPropertyClassObjectIndex,
                        nullptr,
                        nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "wrong ObjectProperty class object index was accepted for AllowRemoteAddToInventory");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            WriteObject(fixture.BoolPropertyClass, kBoolPropertyClassNameIndex, 3, nullptr, nullptr);

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong BoolProperty class object index was accepted");
        }
    }

    void TestRejectsCyclicPropertyChain()
    {
        InventoryFixture fixture;
        BuildAllowRemoteAdd(fixture);
        WriteAt(fixture.PropertyB, 0x28, fixture.PropertyA.data());

        InventoryReflection::InventoryInvocation invocation;
        ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "cyclic inventory property chain was accepted");
    }

    void RequireRejectedNonCanonicalCopiedBool(InventoryFixture& fixture,
                                               size_t paramOffset,
                                               const char* message)
    {
        fixture.Params[paramOffset] = 2;

        InventoryReflection::InventoryInvocation invocation;
        ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, message);
        Require(invocation.FunctionNameIndex == -1, "rejected inventory bool left stale function name");
        Require(invocation.OuterNameIndex == -1, "rejected inventory bool left stale outer name");
        Require(!invocation.HasParameterRanges, "rejected inventory bool left stale parameter-range state");
        Require(invocation.Fields.empty(), "rejected inventory bool left stale fields");
    }

    void TestRejectsNonCanonicalCopiedBoolParams()
    {
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            fixture.Params[1] = 1;
            RequireRejectedNonCanonicalCopiedBool(fixture,
                                                  0,
                                                  "non-canonical CanUse bIgnoreCooldown was accepted");
        }
        {
            InventoryFixture fixture;
            BuildCanUse(fixture);
            fixture.Params[0] = 1;
            fixture.Params[1] = 0xff;

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "non-canonical CanUse ReturnValue was accepted");
            Require(invocation.FunctionNameIndex == -1, "rejected CanUse return left stale function name");
            Require(invocation.Fields.empty(), "rejected CanUse return left stale fields");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            fixture.Params[0x11] = 1;
            RequireRejectedNonCanonicalCopiedBool(
                fixture,
                0x10,
                "non-canonical AllowRemoteAddToInventory bRequestedByPlayer was accepted");
        }
        {
            InventoryFixture fixture;
            BuildAllowRemoteAdd(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 0xff;

            InventoryReflection::InventoryInvocation invocation;
            ReadResult result = InventoryReflection::TryIdentifyInventoryInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "non-canonical AllowRemoteAddToInventory ReturnValue was accepted");
            Require(invocation.FunctionNameIndex == -1, "rejected remote-add return left stale function name");
            Require(invocation.Fields.empty(), "rejected remote-add return left stale fields");
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
    TestRecognizesInventoryActionsAsMetadataOnly();
    TestRejectsWrongOuterAndNameNumber();
    TestRejectsWrongFunctionClass();
    TestRejectsWrongShape();
    TestRejectsWrongPropertyMetadata();
    TestRejectsCyclicPropertyChain();
    TestRejectsNonCanonicalCopiedBoolParams();
    TestGateRejectsBeforeReading();

    std::cout << "InventoryReflectionTests passed\n";
    return 0;
}
