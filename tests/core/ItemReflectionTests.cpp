#include "ue/ItemReflection.h"

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

    constexpr int32_t kAllowEquipItemNameIndex = 6235;
    constexpr int32_t kCanRepairNameIndex = 6250;
    constexpr int32_t kCraftBlueprintNameIndex = 6257;
    constexpr int32_t kUseItemOntoItemNameIndex = 6346;
    constexpr int32_t kPrimalItemNameIndex = 6231;
    constexpr int32_t kPrimalItemObjectIndex = 17;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBIgnoreInventoryRequirementNameIndex = 18617;
    constexpr int32_t kToInventoryNameIndex = 18795;
    constexpr int32_t kDestinationItemNameIndex = 19285;
    constexpr int32_t kAdditionalDataNameIndex = 19290;
    constexpr int32_t kBConsumeResourcesNameIndex = 19293;
    constexpr uint32_t kItemFunctionFlags = 0x04020400;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint64_t kToInventoryPropertyFlags = 0x1044080280;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kIntInputPropertyFlags = 0x1040000280;

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

    struct ItemFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> IntPropertyClass{};
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
            Context.Regions.push_back({ObjectPropertyClass.data(), ObjectPropertyClass.size()});
            Context.Regions.push_back({IntPropertyClass.data(), IntPropertyClass.size()});
            Context.Regions.push_back({BoolPropertyClass.data(), BoolPropertyClass.size()});
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

    void InitClasses(ItemFixture& fixture)
    {
        WriteObject(fixture.ObjectPropertyClass,
                    kObjectPropertyClassNameIndex,
                    kObjectPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.IntPropertyClass,
                    kIntPropertyClassNameIndex,
                    kIntPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.BoolPropertyClass,
                    kBoolPropertyClassNameIndex,
                    kBoolPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(ItemFixture& fixture,
                       int32_t functionNameIndex,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 3>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kPrimalItemNameIndex, kPrimalItemObjectIndex, nullptr, nullptr);
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
        WriteAt(fixture.Function, 0x90, kItemFunctionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildAllowEquipItem(ItemFixture& fixture)
    {
        BuildFunction(fixture,
                      kAllowEquipItemNameIndex,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kToInventoryNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kToInventoryPropertyFlags},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                      }});
    }

    void BuildCanRepair(ItemFixture& fixture)
    {
        BuildFunction(fixture,
                      kCanRepairNameIndex,
                      2,
                      0x02,
                      0x01,
                      {{
                          {kBIgnoreInventoryRequirementNameIndex,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kReturnValueNameIndex, 0x01, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                      }});
    }

    void BuildCraftBlueprint(ItemFixture& fixture)
    {
        BuildFunction(fixture,
                      kCraftBlueprintNameIndex,
                      1,
                      0x01,
                      0xffff,
                      {{
                          {kBConsumeResourcesNameIndex,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {},
                          {},
                      }});
    }

    void BuildUseItemOntoItem(ItemFixture& fixture)
    {
        BuildFunction(fixture,
                      kUseItemOntoItemNameIndex,
                      3,
                      0x0d,
                      0x0c,
                      {{
                          {kDestinationItemNameIndex,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kAdditionalDataNameIndex, 0x08, 0x04, fixture.IntPropertyClass.data(), kIntInputPropertyFlags},
                          {kReturnValueNameIndex, 0x0c, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void RequireFieldMetadata(const ItemReflection::ItemFieldRange& field,
                              ItemReflection::ItemField expectedField,
                              int32_t expectedNameIndex,
                              int32_t expectedOffset,
                              size_t expectedSize,
                              bool expectedExposesRange)
    {
        Require(field.Field == expectedField, "item field kind mismatch");
        Require(field.PropertyNameIndex == expectedNameIndex, "item field FName mismatch");
        Require(field.Offset == expectedOffset, "item field offset mismatch");
        Require(field.Size == expectedSize, "item field size mismatch");
        Require(field.ExposesRange == expectedExposesRange, "item field exposure mismatch");
    }

    void TestRecognizesAllowEquipItemWithObjectMetadataOnly()
    {
        ItemFixture fixture;
        BuildAllowEquipItem(fixture);
        fixture.Params[0x08] = 1;

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ItemReflection::ItemFunction::AllowEquipItem, "AllowEquipItem kind mismatch");
        Require(invocation.FunctionNameIndex == kAllowEquipItemNameIndex, "AllowEquipItem function index mismatch");
        Require(invocation.OuterNameIndex == kPrimalItemNameIndex, "AllowEquipItem outer index mismatch");
        Require(invocation.HasParameterRanges, "AllowEquipItem did not report provided params");
        Require(invocation.Fields.size() == 2, "AllowEquipItem field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             ItemReflection::ItemField::ToInventory,
                             kToInventoryNameIndex,
                             0x00,
                             0x08,
                             false);
        Require(invocation.Fields[0].Range.Data == nullptr, "toInventory range should not be exposed");
        RequireFieldMetadata(invocation.Fields[1],
                             ItemReflection::ItemField::ReturnValue,
                             kReturnValueNameIndex,
                             0x08,
                             0x01,
                             true);
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                "AllowEquipItem ReturnValue range mismatch");
        Require(invocation.Fields[1].Range.Size == 0x01, "AllowEquipItem ReturnValue range size mismatch");
    }

    void TestRecognizesCanRepairBoolRanges()
    {
        ItemFixture fixture;
        BuildCanRepair(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x01] = 0;

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ItemReflection::ItemFunction::CanRepair, "CanRepair kind mismatch");
        Require(invocation.Fields.size() == 2, "CanRepair field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             ItemReflection::ItemField::BIgnoreInventoryRequirement,
                             kBIgnoreInventoryRequirementNameIndex,
                             0x00,
                             0x01,
                             true);
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(),
                "bIgnoreInventoryRequirement range mismatch");
        Require(invocation.Fields[0].Range.Size == 0x01,
                "bIgnoreInventoryRequirement range size mismatch");
        RequireFieldMetadata(invocation.Fields[1],
                             ItemReflection::ItemField::ReturnValue,
                             kReturnValueNameIndex,
                             0x01,
                             0x01,
                             true);
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x01,
                "CanRepair ReturnValue range mismatch");
    }

    void TestRecognizesCraftBlueprintBoolRange()
    {
        ItemFixture fixture;
        BuildCraftBlueprint(fixture);
        fixture.Params[0x00] = 1;

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ItemReflection::ItemFunction::CraftBlueprint,
                "CraftBlueprint kind mismatch");
        Require(invocation.Fields.size() == 1, "CraftBlueprint field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             ItemReflection::ItemField::BConsumeResources,
                             kBConsumeResourcesNameIndex,
                             0x00,
                             0x01,
                             true);
        Require(invocation.Fields[0].Range.Data == fixture.Params.data(),
                "bConsumeResources range mismatch");
        Require(invocation.Fields[0].Range.Size == 0x01, "bConsumeResources range size mismatch");
    }

    void TestRecognizesUseItemOntoItemWithOnlyBoolRange()
    {
        ItemFixture fixture;
        BuildUseItemOntoItem(fixture);
        fixture.Params[0x08] = 0x7f;
        fixture.Params[0x0c] = 1;

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == ItemReflection::ItemFunction::UseItemOntoItem,
                "UseItemOntoItem kind mismatch");
        Require(invocation.Fields.size() == 3, "UseItemOntoItem field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             ItemReflection::ItemField::DestinationItem,
                             kDestinationItemNameIndex,
                             0x00,
                             0x08,
                             false);
        Require(invocation.Fields[0].Range.Data == nullptr, "DestinationItem range should not be exposed");
        RequireFieldMetadata(invocation.Fields[1],
                             ItemReflection::ItemField::AdditionalData,
                             kAdditionalDataNameIndex,
                             0x08,
                             0x04,
                             false);
        Require(invocation.Fields[1].Range.Data == nullptr, "AdditionalData range should not be exposed");
        Require(invocation.Fields[1].Range.Size == 0, "AdditionalData range size should not be exposed");
        RequireFieldMetadata(invocation.Fields[2],
                             ItemReflection::ItemField::ReturnValue,
                             kReturnValueNameIndex,
                             0x0c,
                             0x01,
                             true);
        Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x0c,
                "UseItemOntoItem ReturnValue range mismatch");
    }

    void TestMetadataOnlyItemFieldsAreNotReadFromParams()
    {
        ItemFixture fixture;
        BuildUseItemOntoItem(fixture);
        fixture.Params[0x0c] = 1;

        MemoryReader reader = fixture.Reader();
        fixture.Context.Regions.pop_back();
        fixture.Context.Regions.push_back({fixture.Params.data() + 0x0c, 1});

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            reader,
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Fields.size() == 3, "UseItemOntoItem metadata-only field count mismatch");
        Require(invocation.Fields[0].Range.Data == nullptr, "DestinationItem range should not be exposed");
        Require(invocation.Fields[1].Range.Data == nullptr, "AdditionalData range should not be exposed");
        Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x0c,
                "UseItemOntoItem ReturnValue range mismatch with narrow params reader");
    }

    void TestNullParamsProduceMetadataOnlyRanges()
    {
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                nullptr,
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(!invocation.HasParameterRanges, "null params should produce metadata-only CanRepair invocation");
            Require(invocation.Fields.size() == 2, "metadata-only CanRepair field count mismatch");
            for (const ItemReflection::ItemFieldRange& field : invocation.Fields)
            {
                Require(field.Range.Data == nullptr, "null params exposed CanRepair parameter data");
                Require(field.Range.Size == 0, "null params exposed CanRepair parameter size");
            }
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                nullptr,
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(!invocation.HasParameterRanges,
                    "null params should produce metadata-only UseItemOntoItem invocation");
            Require(invocation.Fields.size() == 3, "metadata-only UseItemOntoItem field count mismatch");
            for (const ItemReflection::ItemFieldRange& field : invocation.Fields)
            {
                Require(field.Range.Data == nullptr, "null params exposed UseItemOntoItem parameter data");
                Require(field.Range.Size == 0, "null params exposed UseItemOntoItem parameter size");
            }
        }
    }

    void TestRejectsNonCanonicalBoolBytes()
    {
        {
            ItemFixture fixture;
            BuildAllowEquipItem(fixture);
            fixture.Params[0x08] = 2;

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "non-canonical AllowEquipItem ReturnValue was accepted");
            Require(invocation.Fields.empty(), "rejected AllowEquipItem left stale fields");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            fixture.Params[0x00] = 2;
            fixture.Params[0x01] = 1;

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "non-canonical CanRepair input bool was accepted");
            Require(invocation.Fields.empty(), "rejected CanRepair input left stale fields");
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);
            fixture.Params[0x0c] = 2;

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible,
                    "non-canonical UseItemOntoItem ReturnValue was accepted");
            Require(invocation.Fields.empty(), "rejected UseItemOntoItem left stale fields");
        }
    }

    void TestRejectsWrongOuterAndNameNumber()
    {
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.Outer, 9999, kPrimalItemObjectIndex, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item outer was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.Outer, kPrimalItemNameIndex, 9999, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item outer object index was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.Outer, kPrimalItemNameIndex, kPrimalItemObjectIndex, nullptr, nullptr, 1);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered item outer FName was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.Function,
                        kCanRepairNameIndex,
                        kCanRepairNameIndex,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data(),
                        1);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered item UFunction FName was accepted");
        }
    }

    void TestRejectsWrongFunctionClass()
    {
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.Function,
                        kCanRepairNameIndex,
                        kCanRepairNameIndex,
                        nullptr,
                        fixture.Outer.data());

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "null item function class was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, 9999, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item function class object index was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.FunctionClass, 9999, kFunctionClassObjectIndex, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item function class FName was accepted");
        }
    }

    void TestRejectsWrongShapeAndPropertyChain()
    {
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{kItemFunctionFlags ^ 0x400});

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item FunctionFlags were accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteAt(fixture.Function, 0x96, uint16_t{3});

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item NumParms was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x03});

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item ParmsSize was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteAt(fixture.Function, 0x9a, uint16_t{0x00});

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item ReturnValueOffset was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kReturnValueNameIndex,
                          0x00,
                          0x01,
                          kBoolInputPropertyFlags);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item first property FName was accepted");
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);
            WriteProperty(fixture.PropertyB,
                          fixture.PropertyC.data(),
                          fixture.Function.data(),
                          fixture.IntPropertyClass.data(),
                          kAdditionalDataNameIndex,
                          0x08,
                          0x04,
                          kIntInputPropertyFlags ^ 0x400);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item property flags were accepted");
        }
        {
            ItemFixture fixture;
            BuildAllowEquipItem(fixture);
            WriteObject(fixture.ObjectPropertyClass, kObjectPropertyClassNameIndex, 9999, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item object property class index was accepted");
        }
        {
            ItemFixture fixture;
            BuildCanRepair(fixture);
            WriteObject(fixture.BoolPropertyClass, kBoolPropertyClassNameIndex, 9999, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item bool property class index was accepted");
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);
            WriteObject(fixture.IntPropertyClass, kIntPropertyClassNameIndex, 9999, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item int property class index was accepted");
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);
            WriteObject(fixture.IntPropertyClass, 9999, kIntPropertyClassObjectIndex, nullptr, nullptr);

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong item int property class FName was accepted");
        }
        {
            ItemFixture fixture;
            BuildUseItemOntoItem(fixture);
            WriteAt(fixture.PropertyB, 0x28, fixture.PropertyA.data());

            ItemReflection::ItemInvocation invocation;
            ReadResult result = ItemReflection::TryIdentifyItemInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "cyclic item property chain was accepted");
        }
    }

    void TestGateRejectsBeforeReading()
    {
        ItemFixture fixture;
        BuildCanRepair(fixture);

        ItemReflection::ItemInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled item reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported item reflection was accepted");

        FieldLayout mutated = *FindSupportedLayout(kSupportedShooterGameServerSha256);
        mutated.UFunctionParmsSize = 0x99;
        ReadOptions wrongLayout;
        wrongLayout.Enabled = true;
        wrongLayout.Layout = &mutated;

        result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            wrongLayout,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "mutated item layout was accepted");
    }

    void TestRejectsClearStaleInvocation()
    {
        ItemFixture fixture;
        BuildCanRepair(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x01] = 1;

        ItemReflection::ItemInvocation invocation;
        ReadResult result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.FunctionNameIndex == kCanRepairNameIndex,
                "valid item invocation did not populate stale source");
        Require(invocation.Fields.size() == 2, "valid item invocation did not populate fields");

        WriteAt(fixture.Function, 0x98, uint16_t{0x03});
        result = ItemReflection::TryIdentifyItemInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "invalid item invocation was accepted");
        Require(invocation.FunctionNameIndex == -1, "rejected item invocation left stale function name");
        Require(invocation.OuterNameIndex == -1, "rejected item invocation left stale outer name");
        Require(!invocation.HasParameterRanges, "rejected item invocation left stale range state");
        Require(invocation.Fields.empty(), "rejected item invocation left stale fields");
    }
}

int main()
{
    TestRecognizesAllowEquipItemWithObjectMetadataOnly();
    TestRecognizesCanRepairBoolRanges();
    TestRecognizesCraftBlueprintBoolRange();
    TestRecognizesUseItemOntoItemWithOnlyBoolRange();
    TestMetadataOnlyItemFieldsAreNotReadFromParams();
    TestNullParamsProduceMetadataOnlyRanges();
    TestRejectsNonCanonicalBoolBytes();
    TestRejectsWrongOuterAndNameNumber();
    TestRejectsWrongFunctionClass();
    TestRejectsWrongShapeAndPropertyChain();
    TestGateRejectsBeforeReading();
    TestRejectsClearStaleInvocation();

    std::cout << "ItemReflectionTests passed\n";
    return 0;
}
