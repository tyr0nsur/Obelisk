#include "ue/BuffReflection.h"

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

    constexpr int32_t kAllowPostProcessEffectNameIndex = 1073;
    constexpr int32_t kBPOnBuffLifetimeUpdatedNameIndex = 1129;
    constexpr int32_t kBPBuffPreventUploadingNameIndex = 1236;
    constexpr int32_t kBPCustomAllowAddBuffNameIndex = 1288;
    constexpr int32_t kBPPreventAddingOtherBuffNameIndex = 1690;
    constexpr int32_t kBuffOverrideInventoryAccessInputNameIndex = 1814;
    constexpr int32_t kPrimalBuffNameIndex = 7843;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kClassPropertyClassNameIndex = 8;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kClassPropertyClassObjectIndex = 535;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kForCharacterNameIndex = 17726;
    constexpr int32_t kDamageCauserNameIndex = 19001;
    constexpr int32_t kAnotherBuffClassNameIndex = 24180;
    constexpr int32_t kBInputPressedNameIndex = 24188;
    constexpr int32_t kInControllerNameIndex = 24189;

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

    struct BuffFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> ClassPropertyClass{};
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
            Context.Regions.push_back({Outer.data(), Outer.size()});
            Context.Regions.push_back({Params.data(), Params.size()});
            return {RegionReader, &Context};
        }
    };

    ReadOptions Options()
    {
        return MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, true);
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
    }

    void BuildFunction(BuffFixture& fixture,
                       int32_t functionNameIndex,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 3>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kPrimalBuffNameIndex, kPrimalBuffNameIndex, nullptr, nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    reinterpret_cast<const void*>(0x20000),
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
                          fields[i].ElementSize);
        }

        const uint32_t functionFlags = 0x204000;
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
                      1,
                      0x01,
                      0x00,
                      {{
                          {kReturnValueNameIndex, 0x00, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                          {},
                      }});
    }

    void BuildZeroParam(BuffFixture& fixture)
    {
        BuildFunction(fixture, kBPOnBuffLifetimeUpdatedNameIndex, 0, 0x00, 0xffff, {{{}, {}, {}}});
    }

    void BuildBuffOverrideInventoryAccessInput(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBuffOverrideInventoryAccessInputNameIndex,
                      3,
                      0x0a,
                      0x09,
                      {{
                          {kInControllerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kBInputPressedNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x09, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void BuildBPCustomAllowAddBuff(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPCustomAllowAddBuffNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kForCharacterNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kDamageCauserNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data()},
                          {kReturnValueNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void BuildBPPreventAddingOtherBuff(BuffFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPPreventAddingOtherBuffNameIndex,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kAnotherBuffClassNameIndex, 0x00, 0x08, fixture.ClassPropertyClass.data()},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                      }});
    }

    void TestRecognizesBoolReturnTargets()
    {
        for (const auto [nameIndex, function] :
             {std::pair{kAllowPostProcessEffectNameIndex, BuffReflection::BuffFunction::AllowPostProcessEffect},
              std::pair{kBPBuffPreventUploadingNameIndex, BuffReflection::BuffFunction::BPBuffPreventUploading}})
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, nameIndex);
            fixture.Params[0] = 1;

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == function, "bool-return buff function mismatch");
            Require(invocation.Fields.size() == 1, "bool-return field count mismatch");
            Require(invocation.Fields[0].Field == BuffReflection::BuffField::ReturnValue,
                    "bool-return ReturnValue field mismatch");
            Require(invocation.Fields[0].Range.Data == fixture.Params.data(), "bool-return range mismatch");
        }
    }

    void TestRecognizesZeroParamWithoutParamRead()
    {
        BuffFixture fixture;
        BuildZeroParam(fixture);

        BuffReflection::BuffInvocation invocation;
        ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            reinterpret_cast<const void*>(0x1),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == BuffReflection::BuffFunction::BPOnBuffLifetimeUpdated,
                "zero-param buff function mismatch");
        Require(invocation.Fields.empty(), "zero-param function exposed fields");
    }

    void TestRecognizesObjectAndClassTargetsWithoutPointerRanges()
    {
        {
            BuffFixture fixture;
            BuildBuffOverrideInventoryAccessInput(fixture);
            fixture.Params[0x08] = 1;
            fixture.Params[0x09] = 1;

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == BuffReflection::BuffFunction::BuffOverrideInventoryAccessInput,
                    "BuffOverrideInventoryAccessInput kind mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr, "object pointer range should not be exposed");
            Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                    "bInputPressed range mismatch");
            Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x09,
                    "ReturnValue range mismatch");
        }
        {
            BuffFixture fixture;
            BuildBPCustomAllowAddBuff(fixture);
            fixture.Params[0x10] = 1;

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == BuffReflection::BuffFunction::BPCustomAllowAddBuff,
                    "BPCustomAllowAddBuff kind mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr, "forCharacter range should not be exposed");
            Require(invocation.Fields[1].Range.Data == nullptr, "DamageCauser range should not be exposed");
            Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x10,
                    "ReturnValue range mismatch");
        }
        {
            BuffFixture fixture;
            BuildBPPreventAddingOtherBuff(fixture);
            fixture.Params[0x08] = 1;

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == BuffReflection::BuffFunction::BPPreventAddingOtherBuff,
                    "BPPreventAddingOtherBuff kind mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr, "ClassProperty range should not be exposed");
            Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                    "ReturnValue range mismatch");
        }
    }

    void TestRejectsWrongOuterAndNameNumber()
    {
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteObject(fixture.Outer, 9999, 9999, nullptr, nullptr);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong outer was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteObject(fixture.Function,
                        kAllowPostProcessEffectNameIndex,
                        kAllowPostProcessEffectNameIndex,
                        reinterpret_cast<const void*>(0x20000),
                        fixture.Outer.data(),
                        1);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
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
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.Function, 0x98, uint16_t{0x02});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong ParmsSize was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.Function, 0x96, uint16_t{0x02});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "unexpected property count was accepted");
        }
        {
            BuffFixture fixture;
            BuildBuffOverrideInventoryAccessInput(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kInControllerNameIndex,
                          0x00,
                          0x01);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong object property class was accepted");
        }
        {
            BuffFixture fixture;
            BuildBPPreventAddingOtherBuff(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.ObjectPropertyClass.data(),
                          kAnotherBuffClassNameIndex,
                          0x00,
                          0x08);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong class property class was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.Function, 0x9a, uint16_t{0x01});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong ReturnValueOffset was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteProperty(fixture.PropertyA,
                          nullptr,
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kReturnValueNameIndex,
                          0x01,
                          0x01);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong property offset was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteProperty(fixture.PropertyA,
                          nullptr,
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kReturnValueNameIndex,
                          0x00,
                          0x02);

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong property size was accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.PropertyA, 0x30, int32_t{2});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong ArrayDim was accepted");
        }
    }

    void TestRejectsUnsupportedTarget()
    {
        BuffFixture fixture;
        BuildBoolReturn(fixture, 9999);

        BuffReflection::BuffInvocation invocation;
        ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "unsupported buff target was accepted");
    }

    void TestGateRejectsBeforeReading()
    {
        BuffFixture fixture;
        BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);

        BuffReflection::BuffInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled buff reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = BuffReflection::TryIdentifyBuffInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported buff reflection was accepted");
    }
}

int main()
{
    TestRecognizesBoolReturnTargets();
    TestRecognizesZeroParamWithoutParamRead();
    TestRecognizesObjectAndClassTargetsWithoutPointerRanges();
    TestRejectsWrongOuterAndNameNumber();
    TestRejectsWrongShape();
    TestRejectsUnsupportedTarget();
    TestGateRejectsBeforeReading();

    std::cout << "BuffReflectionTests passed\n";
    return 0;
}
