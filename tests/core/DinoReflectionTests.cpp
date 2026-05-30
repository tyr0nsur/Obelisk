#include "ue/DinoReflection.h"

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

    constexpr int32_t kAddPassengerNameIndex = 8267;
    constexpr int32_t kAllowCarryCharacterNameIndex = 8269;
    constexpr int32_t kPrimalDinoCharacterNameIndex = 8265;
    constexpr int32_t kBPNotifyAddPassengerSyntheticNameIndex = 36;
    constexpr int32_t kBPAllowCarryCharacterSyntheticNameIndex = 77;
    constexpr int32_t kIntPropertyClassNameIndex = 2;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kIntPropertyClassObjectIndex = 539;
    constexpr int32_t kACharacterNameIndex = 4044;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kBSkipLineTraceNameIndex = 25580;
    constexpr int32_t kBAllowFlyersAndWaterDinosNameIndex = 25581;
    constexpr int32_t kBForcePassengerNameIndex = 25582;
    constexpr int32_t kPassengerSeatIndexNameIndex = 25583;
    constexpr int32_t kCanCarryPawnNameIndex = 25584;

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

    struct DinoFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x80> PropertyE{};
        std::array<uint8_t, 0x80> PropertyF{};
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
            Context.Regions.push_back({PropertyD.data(), PropertyD.size()});
            Context.Regions.push_back({PropertyE.data(), PropertyE.size()});
            Context.Regions.push_back({PropertyF.data(), PropertyF.size()});
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

    void InitClasses(DinoFixture& fixture)
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

    void BuildFunction(DinoFixture& fixture,
                       int32_t functionNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 6>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer,
                    kPrimalDinoCharacterNameIndex,
                    kPrimalDinoCharacterNameIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());

        std::array<std::array<uint8_t, 0x80>*, 6> properties{
            &fixture.PropertyA,
            &fixture.PropertyB,
            &fixture.PropertyC,
            &fixture.PropertyD,
            &fixture.PropertyE,
            &fixture.PropertyF,
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

        WriteAt(fixture.Function, 0x38, numParms > 0 ? fixture.PropertyA.data() : nullptr);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildAddPassenger(DinoFixture& fixture, int32_t functionNameIndex = kAddPassengerNameIndex)
    {
        BuildFunction(fixture,
                      functionNameIndex,
                      0x04020401,
                      6,
                      0x10,
                      0x0f,
                      {{
                          {kACharacterNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kPassengerSeatIndexNameIndex, 0x08, 0x04, fixture.IntPropertyClass.data()},
                          {kBForcePassengerNameIndex, 0x0c, 0x01, fixture.BoolPropertyClass.data()},
                          {kBAllowFlyersAndWaterDinosNameIndex, 0x0d, 0x01, fixture.BoolPropertyClass.data()},
                          {kBSkipLineTraceNameIndex, 0x0e, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x0f, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void BuildAllowCarryCharacter(DinoFixture& fixture,
                                  int32_t functionNameIndex = kAllowCarryCharacterNameIndex)
    {
        BuildFunction(fixture,
                      functionNameIndex,
                      0x04020400,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kCanCarryPawnNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                          {},
                          {},
                          {},
                      }});
    }

    void TestRecognizesAddPassengerWithoutObjectRange()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);
        fixture.Params[0x08] = 7;
        fixture.Params[0x0c] = 1;
        fixture.Params[0x0d] = 0;
        fixture.Params[0x0e] = 1;
        fixture.Params[0x0f] = 1;

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == DinoReflection::DinoFunction::AddPassenger, "AddPassenger kind mismatch");
        Require(invocation.Fields.size() == 6, "AddPassenger field count mismatch");
        Require(invocation.Fields[0].Field == DinoReflection::DinoField::ACharacter,
                "ACharacter field mismatch");
        Require(!invocation.Fields[0].ExposesRange, "ACharacter should be recognition-only");
        Require(invocation.Fields[0].Range.Data == nullptr, "ACharacter range should not be exposed");
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                "PassengerSeatIndex range mismatch");
        Require(invocation.Fields[1].Range.Size == 4, "PassengerSeatIndex range size mismatch");
        Require(invocation.Fields[2].Range.Data == fixture.Params.data() + 0x0c,
                "bForcePassenger range mismatch");
        Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x0d,
                "bAllowFlyersAndWaterDinos range mismatch");
        Require(invocation.Fields[4].Range.Data == fixture.Params.data() + 0x0e,
                "bSkipLineTrace range mismatch");
        Require(invocation.Fields[5].Range.Data == fixture.Params.data() + 0x0f,
                "ReturnValue range mismatch");
    }

    void TestRecognizesAllowCarryCharacterWithoutObjectRange()
    {
        DinoFixture fixture;
        BuildAllowCarryCharacter(fixture);
        fixture.Params[0x08] = 1;

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == DinoReflection::DinoFunction::AllowCarryCharacter,
                "AllowCarryCharacter kind mismatch");
        Require(invocation.Fields.size() == 2, "AllowCarryCharacter field count mismatch");
        Require(invocation.Fields[0].Field == DinoReflection::DinoField::CanCarryPawn,
                "CanCarryPawn field mismatch");
        Require(invocation.Fields[0].Range.Data == nullptr, "CanCarryPawn range should not be exposed");
        Require(invocation.Fields[1].Range.Data == fixture.Params.data() + 0x08,
                "AllowCarryCharacter ReturnValue range mismatch");
    }

    void TestAcceptsMetadataOnlyRecognition()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            nullptr,
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(!invocation.HasParameterRanges, "metadata-only dino recognition reported parameter ranges");
        Require(invocation.Fields[1].Range.Data == nullptr, "metadata-only scalar range should stay empty");
    }

    void TestRejectsPartialNameCollisions()
    {
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture, kBPNotifyAddPassengerSyntheticNameIndex);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "BPNotifyAddPassenger-like target was accepted");
        }
        {
            DinoFixture fixture;
            BuildAllowCarryCharacter(fixture, kBPAllowCarryCharacterSyntheticNameIndex);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "BPAllowCarryCharacter-like target was accepted");
        }
    }

    void TestRejectsWrongOuterNameNumberAndClass()
    {
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteObject(fixture.Outer, 9999, 9999, nullptr, nullptr);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong dino outer was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteObject(fixture.Outer,
                        kPrimalDinoCharacterNameIndex,
                        kPrimalDinoCharacterNameIndex,
                        nullptr,
                        nullptr,
                        1);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered dino outer FName was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteObject(fixture.Function,
                        kAddPassengerNameIndex,
                        kAddPassengerNameIndex,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data(),
                        1);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered dino UFunction FName was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteObject(fixture.FunctionClass, 9999, kFunctionClassObjectIndex, nullptr, nullptr);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong UFunction class was accepted");
        }
    }

    void TestAcceptsSemanticClassNamesWithDifferentInternalIndices()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, 9001, nullptr, nullptr);
        WriteObject(fixture.ObjectPropertyClass, kObjectPropertyClassNameIndex, 9002, nullptr, nullptr);
        WriteObject(fixture.IntPropertyClass, kIntPropertyClassNameIndex, 9003, nullptr, nullptr);
        WriteObject(fixture.BoolPropertyClass, kBoolPropertyClassNameIndex, 9004, nullptr, nullptr);

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == DinoReflection::DinoFunction::AddPassenger,
                "semantic class-name dino recognition kind mismatch");
    }

    void TestRejectsWrongShape()
    {
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{0x04020400});

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong dino FunctionFlags were accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x11});

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong AddPassenger ParmsSize was accepted");
        }
        {
            DinoFixture fixture;
            BuildAllowCarryCharacter(fixture);
            WriteAt(fixture.Function, 0x9a, uint16_t{0x09});

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong AllowCarryCharacter ReturnValueOffset was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteProperty(fixture.PropertyB,
                          fixture.PropertyC.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kPassengerSeatIndexNameIndex,
                          0x08,
                          0x01);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong int property class was accepted");
        }
        {
            DinoFixture fixture;
            BuildAllowCarryCharacter(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.ObjectPropertyClass.data(),
                          kCanCarryPawnNameIndex,
                          0x01,
                          0x08);

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong object property offset was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteAt(fixture.PropertyC, 0x30, int32_t{2});

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong bool property ArrayDim was accepted");
        }
    }

    void TestRejectsNullFunction()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            Options(),
            nullptr,
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::InvalidArgument, "null dino UFunction was accepted");
    }

    void TestRejectsUnreadableScalarRange()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);
        MemoryReader reader = fixture.Reader();
        fixture.Context.Regions.back().Size = 0x08;

        DinoReflection::DinoInvocation invocation;
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            reader,
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Unreadable, "unreadable dino scalar range was accepted");
    }

    void TestRejectsTruncatedAndOverlongPropertyChains()
    {
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteAt(fixture.PropertyC, 0x28, static_cast<const void*>(nullptr));

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "truncated dino property chain was accepted");
        }
        {
            DinoFixture fixture;
            BuildAddPassenger(fixture);
            WriteAt(fixture.PropertyF, 0x28, static_cast<const void*>(fixture.PropertyA.data()));

            DinoReflection::DinoInvocation invocation;
            ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "overlong dino property chain was accepted");
        }
    }

    void TestGateRejectsBeforeReading()
    {
        DinoFixture fixture;
        BuildAddPassenger(fixture);

        DinoReflection::DinoInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled dino reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = DinoReflection::TryIdentifyDinoInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported dino reflection was accepted");
    }
}

int main()
{
    TestRecognizesAddPassengerWithoutObjectRange();
    TestRecognizesAllowCarryCharacterWithoutObjectRange();
    TestAcceptsMetadataOnlyRecognition();
    TestRejectsPartialNameCollisions();
    TestRejectsWrongOuterNameNumberAndClass();
    TestAcceptsSemanticClassNamesWithDifferentInternalIndices();
    TestRejectsWrongShape();
    TestRejectsNullFunction();
    TestRejectsUnreadableScalarRange();
    TestRejectsTruncatedAndOverlongPropertyChains();
    TestGateRejectsBeforeReading();

    std::cout << "DinoReflectionTests passed\n";
    return 0;
}
