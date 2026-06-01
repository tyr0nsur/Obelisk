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
    constexpr uint8_t kBuffBoolFieldSize = 0x01;
    constexpr uint8_t kBuffBoolByteOffset = 0x00;
    constexpr uint8_t kBuffBoolByteMask = 0x01;
    constexpr uint8_t kBuffBoolFieldMask = 0xff;

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

        if (klass)
        {
            FNameValue className{};
            std::memcpy(&className, static_cast<const uint8_t*>(klass) + 0x18, sizeof(className));
            if (className.ComparisonIndex == kBoolPropertyClassNameIndex && className.Number == 0)
            {
                WriteAt(buffer, 0x70, kBuffBoolFieldSize);
                WriteAt(buffer, 0x71, kBuffBoolByteOffset);
                WriteAt(buffer, 0x72, kBuffBoolByteMask);
                WriteAt(buffer, 0x73, kBuffBoolFieldMask);
            }
        }
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
        WriteObject(fixture.FunctionClass,
                    kFunctionClassNameIndex,
                    kFunctionClassObjectIndex,
                    nullptr,
                    nullptr);
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
            Require(invocation.HasParameterRanges, "bool-return parameter ranges missing");
            Require(invocation.ParameterData == fixture.Params.data(), "bool-return parameter provenance data mismatch");
            Require(invocation.ParameterSize == 0x01, "bool-return parameter provenance size mismatch");
            Require(invocation.Fields.size() == 1, "bool-return field count mismatch");
            Require(invocation.Fields[0].Field == BuffReflection::BuffField::ReturnValue,
                    "bool-return ReturnValue field mismatch");
            Require(invocation.Fields[0].PropertyClassNameIndex == kBoolPropertyClassNameIndex,
                    "bool-return property class name mismatch");
            Require(invocation.Fields[0].PropertyClassObjectIndex == kBoolPropertyClassObjectIndex,
                    "bool-return property class object mismatch");
            Require(invocation.Fields[0].PropertyFlags == kBoolReturnPropertyFlags,
                    "bool-return property flags mismatch");
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
            Require(invocation.ParameterData == fixture.Params.data(),
                    "BuffOverrideInventoryAccessInput parameter provenance data mismatch");
            Require(invocation.ParameterSize == 0x0a,
                    "BuffOverrideInventoryAccessInput parameter provenance size mismatch");
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
                        fixture.FunctionClass.data(),
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
            WriteAt(fixture.Function, 0x90, uint32_t{kBuffEventWithReturnFunctionFlags ^ 0x400});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong FunctionFlags were accepted");
        }
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
                          0x01,
                          kBoolInputPropertyFlags);

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
                          0x08,
                          kObjectInputPropertyFlags);

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
                          0x01,
                          kBoolReturnPropertyFlags);

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
                          0x02,
                          kBoolReturnPropertyFlags);

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
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.PropertyA, 0x38, uint64_t{kBoolReturnPropertyFlags ^ 0x400});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong property flags were accepted");
        }
        {
            BuffFixture fixture;
            BuildBoolReturn(fixture, kAllowPostProcessEffectNameIndex);
            WriteAt(fixture.PropertyA, 0x72, uint8_t{0xff});
            WriteAt(fixture.PropertyA, 0x73, uint8_t{0xff});

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong bool property tail metadata was accepted");
        }
    }

    void TestRejectsPropertyChainDrift()
    {
        {
            BuffFixture fixture;
            BuildBuffOverrideInventoryAccessInput(fixture);
            WriteAt(fixture.PropertyB, 0x28, static_cast<const void*>(nullptr));

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "truncated buff property chain was accepted");
        }
        {
            BuffFixture fixture;
            BuildBuffOverrideInventoryAccessInput(fixture);
            WriteAt(fixture.PropertyC, 0x28, fixture.PropertyA.data());

            BuffReflection::BuffInvocation invocation;
            ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "cyclic buff property chain was accepted");
        }
    }

    void TestRejectsNonCanonicalCopiedBoolsAndClearsOutput()
    {
        BuffFixture fixture;
        BuildBuffOverrideInventoryAccessInput(fixture);
        fixture.Params[0x08] = 2;
        fixture.Params[0x09] = 1;

        BuffReflection::BuffInvocation invocation;
        invocation.ParameterData = fixture.Params.data();
        invocation.ParameterSize = fixture.Params.size();
        invocation.HasParameterRanges = true;

        ReadResult result = BuffReflection::TryIdentifyBuffInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "non-canonical buff bool byte was accepted");
        Require(!invocation.HasParameterRanges, "rejected buff attempt kept parameter range flag");
        Require(invocation.ParameterData == nullptr, "rejected buff attempt kept parameter data");
        Require(invocation.ParameterSize == 0, "rejected buff attempt kept parameter size");
        Require(invocation.Fields.empty(), "rejected buff attempt left copied field ranges");
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
    TestRejectsPropertyChainDrift();
    TestRejectsNonCanonicalCopiedBoolsAndClearsOutput();
    TestRejectsUnsupportedTarget();
    TestGateRejectsBeforeReading();

    std::cout << "BuffReflectionTests passed\n";
    return 0;
}
