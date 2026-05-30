#include "ue/MissionReflection.h"

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

    constexpr int32_t kBPAllowPlayerToLeaveMissionNameIndex = 1211;
    constexpr int32_t kBPOnPlayerRemovedFromMissionNameIndex = 1582;
    constexpr int32_t kAddPlayerToMissionNameIndex = 7649;
    constexpr int32_t kMissionTypeNameIndex = 7646;
    constexpr int32_t kGetPlayerUsableItemsNameIndex = 7702;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kArrayPropertyClassNameIndex = 9;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kArrayPropertyClassObjectIndex = 528;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kControllerNameIndex = 5908;
    constexpr int32_t kCharacterNameIndex = 7990;
    constexpr int32_t kPlayerNameIndex = 9972;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kPlayerPawnNameIndex = 21376;
    constexpr int32_t kBForceAddNameIndex = 22956;
    constexpr int32_t kPlayerCharacterNameIndex = 22961;
    constexpr int32_t kBLastPhaseSuccessNameIndex = 22976;
    constexpr int32_t kBFromMissionCompleteEventNameIndex = 22980;
    constexpr int32_t kOutItemIDsNameIndex = 23031;

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

    struct MissionFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
        std::array<uint8_t, 0x40> BoolPropertyClass{};
        std::array<uint8_t, 0x40> ArrayPropertyClass{};
        std::array<uint8_t, 0x40> FunctionClass{};
        std::array<uint8_t, 0x40> Outer{};
        std::array<uint8_t, 0x30> Params{};
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
            Context.Regions.push_back({ArrayPropertyClass.data(), ArrayPropertyClass.size()});
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

    void InitClasses(MissionFixture& fixture)
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
        WriteObject(fixture.ArrayPropertyClass,
                    kArrayPropertyClassNameIndex,
                    kArrayPropertyClassObjectIndex,
                    nullptr,
                    nullptr);
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(MissionFixture& fixture,
                       int32_t functionNameIndex,
                       uint32_t functionFlags,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 4>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kMissionTypeNameIndex, kMissionTypeNameIndex, nullptr, nullptr);
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
                          fields[i].ElementSize);
        }

        WriteAt(fixture.Function, 0x38, numParms > 0 ? fixture.PropertyA.data() : nullptr);
        WriteAt(fixture.Function, 0x90, functionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildGetPlayerUsableItems(MissionFixture& fixture,
                                   int32_t functionNameIndex = kGetPlayerUsableItemsNameIndex)
    {
        BuildFunction(fixture,
                      functionNameIndex,
                      0x04420405,
                      2,
                      0x18,
                      0xffff,
                      {{
                          {kCharacterNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kOutItemIDsNameIndex, 0x08, 0x10, fixture.ArrayPropertyClass.data()},
                          {},
                          {},
                      }});
    }

    void BuildAddPlayerToMission(MissionFixture& fixture,
                                 int32_t functionNameIndex = kAddPlayerToMissionNameIndex)
    {
        BuildFunction(fixture,
                      functionNameIndex,
                      0x04020405,
                      3,
                      0x0a,
                      0x09,
                      {{
                          {kPlayerCharacterNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kBForceAddNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
                          {kReturnValueNameIndex, 0x09, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                      }});
    }

    void BuildBPAllowPlayerToLeaveMission(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPAllowPlayerToLeaveMissionNameIndex,
                      0x0c020c00,
                      2,
                      0x09,
                      0x08,
                      {{
                          {kPlayerPawnNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kReturnValueNameIndex, 0x08, 0x01, fixture.BoolPropertyClass.data()},
                          {},
                          {},
                      }});
    }

    void BuildBPOnPlayerRemovedFromMission(MissionFixture& fixture)
    {
        BuildFunction(fixture,
                      kBPOnPlayerRemovedFromMissionNameIndex,
                      0x0c020c00,
                      4,
                      0x12,
                      0xffff,
                      {{
                          {kPlayerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data()},
                          {kControllerNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data()},
                          {kBFromMissionCompleteEventNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data()},
                          {kBLastPhaseSuccessNameIndex, 0x11, 0x01, fixture.BoolPropertyClass.data()},
                      }});
    }

    void RequireFieldShape(const MissionReflection::MissionFieldRange& field,
                           MissionReflection::MissionField expectedField,
                           int32_t expectedNameIndex,
                           int32_t expectedOffset,
                           size_t expectedSize,
                           bool expectedExposesRange)
    {
        Require(field.Field == expectedField, "mission field semantic mismatch");
        Require(field.PropertyNameIndex == expectedNameIndex, "mission field property name mismatch");
        Require(field.Offset == expectedOffset, "mission field offset mismatch");
        Require(field.Size == expectedSize, "mission field size mismatch");
        Require(field.ExposesRange == expectedExposesRange, "mission field range exposure mismatch");
    }

    void RequireNoRange(const MissionReflection::MissionFieldRange& field, const char* message)
    {
        Require(!field.ExposesRange, message);
        Require(field.Range.Data == nullptr, "recognition-only mission range exposed data");
        Require(field.Range.Size == 0, "recognition-only mission range exposed size");
    }

    void RequireOneByteRange(const MissionReflection::MissionFieldRange& field,
                             const uint8_t* expectedData,
                             const char* message)
    {
        Require(field.ExposesRange, message);
        Require(field.Range.Data == expectedData, "mission bool range data mismatch");
        Require(field.Range.Size == 1, "mission bool range must stay one byte");
    }

    void TestRecognizesGetPlayerUsableItemsWithoutObjectOrArrayRanges()
    {
        MissionFixture fixture;
        BuildGetPlayerUsableItems(fixture);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                "GetPlayerUsableItems kind mismatch");
        Require(invocation.Fields.size() == 2, "GetPlayerUsableItems field count mismatch");
        RequireFieldShape(invocation.Fields[0],
                          MissionReflection::MissionField::Character,
                          kCharacterNameIndex,
                          0x00,
                          0x08,
                          false);
        RequireFieldShape(invocation.Fields[1],
                          MissionReflection::MissionField::OutItemIDs,
                          kOutItemIDsNameIndex,
                          0x08,
                          0x10,
                          false);
        RequireNoRange(invocation.Fields[0], "Character should be recognition-only");
        RequireNoRange(invocation.Fields[1], "OutItemIDs should be recognition-only");
    }

    void TestRecognitionOnlyMissionFieldsDoNotReadParams()
    {
        MissionFixture fixture;
        BuildGetPlayerUsableItems(fixture);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            reinterpret_cast<const void*>(0x22220000),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == MissionReflection::MissionFunction::GetPlayerUsableItems,
                "GetPlayerUsableItems kind mismatch with unreadable params");
        Require(invocation.HasParameterRanges, "non-null params should be recorded as present");
        Require(invocation.Fields.size() == 2, "recognition-only field count mismatch");
        RequireFieldShape(invocation.Fields[0],
                          MissionReflection::MissionField::Character,
                          kCharacterNameIndex,
                          0x00,
                          0x08,
                          false);
        RequireFieldShape(invocation.Fields[1],
                          MissionReflection::MissionField::OutItemIDs,
                          kOutItemIDsNameIndex,
                          0x08,
                          0x10,
                          false);
        RequireNoRange(invocation.Fields[0], "Character should stay recognition-only");
        RequireNoRange(invocation.Fields[1], "OutItemIDs should stay recognition-only");
    }

    void TestRecognizesAddPlayerToMissionBoolRangesOnly()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);
        fixture.Params[0x08] = 1;
        fixture.Params[0x09] = 0;

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == MissionReflection::MissionFunction::AddPlayerToMission,
                "AddPlayerToMission kind mismatch");
        Require(invocation.Fields.size() == 3, "AddPlayerToMission field count mismatch");
        RequireFieldShape(invocation.Fields[0],
                          MissionReflection::MissionField::PlayerCharacter,
                          kPlayerCharacterNameIndex,
                          0x00,
                          0x08,
                          false);
        RequireFieldShape(invocation.Fields[1],
                          MissionReflection::MissionField::BForceAdd,
                          kBForceAddNameIndex,
                          0x08,
                          0x01,
                          true);
        RequireFieldShape(invocation.Fields[2],
                          MissionReflection::MissionField::ReturnValue,
                          kReturnValueNameIndex,
                          0x09,
                          0x01,
                          true);
        RequireNoRange(invocation.Fields[0], "PlayerCharacter range should not be exposed");
        RequireOneByteRange(invocation.Fields[1], fixture.Params.data() + 0x08, "bForceAdd should expose a bool range");
        RequireOneByteRange(invocation.Fields[2],
                            fixture.Params.data() + 0x09,
                            "AddPlayerToMission ReturnValue should expose a bool range");
    }

    void TestUnreadableBoolRangeFailsClosed()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            reinterpret_cast<const void*>(0x33330000),
            invocation);

        Require(!result, "mission bool range was accepted from unreadable params");
    }

    void TestRecognizesLeaveAndRemovedMissionBoolRangesOnly()
    {
        {
            MissionFixture fixture;
            BuildBPAllowPlayerToLeaveMission(fixture);
            fixture.Params[0x08] = 1;

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == MissionReflection::MissionFunction::BPAllowPlayerToLeaveMission,
                    "BPAllowPlayerToLeaveMission kind mismatch");
            Require(invocation.Fields.size() == 2, "BPAllowPlayerToLeaveMission field count mismatch");
            RequireFieldShape(invocation.Fields[0],
                              MissionReflection::MissionField::PlayerPawn,
                              kPlayerPawnNameIndex,
                              0x00,
                              0x08,
                              false);
            RequireFieldShape(invocation.Fields[1],
                              MissionReflection::MissionField::ReturnValue,
                              kReturnValueNameIndex,
                              0x08,
                              0x01,
                              true);
            RequireNoRange(invocation.Fields[0], "PlayerPawn range should not be exposed");
            RequireOneByteRange(invocation.Fields[1],
                                fixture.Params.data() + 0x08,
                                "BPAllowPlayerToLeaveMission ReturnValue should expose a bool range");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            fixture.Params[0x10] = 1;
            fixture.Params[0x11] = 1;

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(invocation.Function == MissionReflection::MissionFunction::BPOnPlayerRemovedFromMission,
                    "BPOnPlayerRemovedFromMission kind mismatch");
            Require(invocation.Fields.size() == 4, "BPOnPlayerRemovedFromMission field count mismatch");
            RequireFieldShape(invocation.Fields[0],
                              MissionReflection::MissionField::Player,
                              kPlayerNameIndex,
                              0x00,
                              0x08,
                              false);
            RequireFieldShape(invocation.Fields[1],
                              MissionReflection::MissionField::Controller,
                              kControllerNameIndex,
                              0x08,
                              0x08,
                              false);
            RequireFieldShape(invocation.Fields[2],
                              MissionReflection::MissionField::BFromMissionCompleteEvent,
                              kBFromMissionCompleteEventNameIndex,
                              0x10,
                              0x01,
                              true);
            RequireFieldShape(invocation.Fields[3],
                              MissionReflection::MissionField::BLastPhaseSuccess,
                              kBLastPhaseSuccessNameIndex,
                              0x11,
                              0x01,
                              true);
            RequireNoRange(invocation.Fields[0], "Player range should not be exposed");
            RequireNoRange(invocation.Fields[1], "Controller range should not be exposed");
            RequireOneByteRange(invocation.Fields[2],
                                fixture.Params.data() + 0x10,
                                "bFromMissionCompleteEvent should expose a bool range");
            RequireOneByteRange(invocation.Fields[3],
                                fixture.Params.data() + 0x11,
                                "bLastPhaseSuccess should expose a bool range");
        }
    }

    void TestAcceptsMetadataOnlyRecognition()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            nullptr,
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(!invocation.HasParameterRanges, "metadata-only mission recognition reported parameter ranges");
        Require(invocation.Fields[1].Range.Data == nullptr, "metadata-only bool range should stay empty");
    }

    void TestRejectsWrongOuterNameNumberAndClass()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteObject(fixture.Outer, 9999, 9999, nullptr, nullptr);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong mission outer was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteObject(fixture.Outer, kMissionTypeNameIndex, kMissionTypeNameIndex, nullptr, nullptr, 1);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered MissionType FName was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteObject(fixture.Function,
                        kAddPlayerToMissionNameIndex,
                        kAddPlayerToMissionNameIndex,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data(),
                        1);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered mission UFunction FName was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteObject(fixture.FunctionClass, 9999, kFunctionClassObjectIndex, nullptr, nullptr);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong mission UFunction class was accepted");
        }
    }

    void TestRejectsWrongShape()
    {
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            WriteAt(fixture.Function, 0x90, uint32_t{0x04020405});

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong mission FunctionFlags were accepted");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x19});

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong GetPlayerUsableItems ParmsSize was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteAt(fixture.Function, 0x9a, uint16_t{0xffff});

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong AddPlayerToMission ReturnValueOffset was accepted");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            WriteProperty(fixture.PropertyB,
                          nullptr,
                          fixture.Function.data(),
                          fixture.ObjectPropertyClass.data(),
                          kOutItemIDsNameIndex,
                          0x08,
                          0x08);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong ArrayProperty class was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            WriteProperty(fixture.PropertyA,
                          fixture.PropertyB.data(),
                          fixture.Function.data(),
                          fixture.BoolPropertyClass.data(),
                          kPlayerNameIndex,
                          0x00,
                          0x01);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong object property class was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteAt(fixture.PropertyB, 0x30, int32_t{2});

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(!result, "wrong mission property ArrayDim was accepted");
        }
    }

    void TestRejectsWrongPropertyNameClassAndChain()
    {
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            const FNameValue wrongName{kReturnValueNameIndex, 0};
            WriteAt(fixture.PropertyB, 0x18, wrongName);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong mission property name was accepted");
        }
        {
            MissionFixture fixture;
            BuildAddPlayerToMission(fixture);
            WriteObject(fixture.BoolPropertyClass,
                        kBoolPropertyClassNameIndex,
                        kBoolPropertyClassObjectIndex,
                        nullptr,
                        nullptr,
                        1);

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "numbered mission property class was accepted");
        }
        {
            MissionFixture fixture;
            BuildBPOnPlayerRemovedFromMission(fixture);
            WriteAt(fixture.PropertyB, 0x28, static_cast<const void*>(nullptr));

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "truncated mission property chain was accepted");
        }
        {
            MissionFixture fixture;
            BuildGetPlayerUsableItems(fixture);
            WriteAt(fixture.PropertyB, 0x28, fixture.PropertyC.data());

            MissionReflection::MissionInvocation invocation;
            ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "overlong mission property chain was accepted");
        }
    }

    void TestAcceptsPropertyClassSemanticNamesWithoutStableInternalIndices()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);
        WriteObject(fixture.ObjectPropertyClass, kObjectPropertyClassNameIndex, 99001, nullptr, nullptr);
        WriteObject(fixture.BoolPropertyClass, kBoolPropertyClassNameIndex, 99002, nullptr, nullptr);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == MissionReflection::MissionFunction::AddPlayerToMission,
                "semantic class FName acceptance changed mission kind");
    }

    void TestRejectsUnsupportedTarget()
    {
        MissionFixture fixture;
        BuildGetPlayerUsableItems(fixture, 9999);

        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "unsupported mission target was accepted");
    }

    void TestGateRejectsBeforeReading()
    {
        MissionFixture fixture;
        BuildAddPlayerToMission(fixture);

        MissionReflection::MissionInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled mission reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported mission reflection was accepted");

        result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            unsupported,
            reinterpret_cast<const void*>(0x44440000),
            reinterpret_cast<const void*>(0x55550000),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout,
                "unsupported mission reflection read memory before failing closed");
    }

    void TestRejectsNullFunction()
    {
        MissionFixture fixture;
        MissionReflection::MissionInvocation invocation;
        ReadResult result = MissionReflection::TryIdentifyMissionInvocation(
            fixture.Reader(),
            Options(),
            nullptr,
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::InvalidArgument, "null mission UFunction pointer was accepted");
    }
}

int main()
{
    TestRecognizesGetPlayerUsableItemsWithoutObjectOrArrayRanges();
    TestRecognitionOnlyMissionFieldsDoNotReadParams();
    TestRecognizesAddPlayerToMissionBoolRangesOnly();
    TestUnreadableBoolRangeFailsClosed();
    TestRecognizesLeaveAndRemovedMissionBoolRangesOnly();
    TestAcceptsMetadataOnlyRecognition();
    TestRejectsWrongOuterNameNumberAndClass();
    TestRejectsWrongShape();
    TestRejectsWrongPropertyNameClassAndChain();
    TestAcceptsPropertyClassSemanticNamesWithoutStableInternalIndices();
    TestRejectsUnsupportedTarget();
    TestGateRejectsBeforeReading();
    TestRejectsNullFunction();

    std::cout << "MissionReflectionTests passed\n";
    return 0;
}
