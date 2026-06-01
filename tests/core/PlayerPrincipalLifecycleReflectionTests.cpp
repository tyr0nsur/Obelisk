#include "ue/PlayerPrincipalLifecycleReflection.h"

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

    constexpr int32_t kHandleNewPlayerNameIndex = 2170;
    constexpr int32_t kOnLogoutNameIndex = 2384;
    constexpr int32_t kShooterGameModeNameIndex = 9755;
    constexpr int32_t kShooterGameModeObjectIndex = 411;
    constexpr int32_t kBoolPropertyClassNameIndex = 3;
    constexpr int32_t kObjectPropertyClassNameIndex = 5;
    constexpr int32_t kFunctionClassNameIndex = 10650;
    constexpr int32_t kBoolPropertyClassObjectIndex = 532;
    constexpr int32_t kObjectPropertyClassObjectIndex = 534;
    constexpr int32_t kFunctionClassObjectIndex = 518;
    constexpr int32_t kReturnValueNameIndex = 17716;
    constexpr int32_t kPlayerDataNameIndex = 21307;
    constexpr int32_t kPlayerCharacterNameIndex = 22961;
    constexpr int32_t kNewPlayerNameIndex = 28411;
    constexpr int32_t kBIsFromLoginNameIndex = 28509;
    constexpr int32_t kExitingNameIndex = 28543;
    constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint8_t kBoolFieldSize = 0x01;
    constexpr uint8_t kBoolByteOffset = 0x00;
    constexpr uint8_t kBoolByteMask = 0x01;
    constexpr uint8_t kBoolFieldMask = 0xff;

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
            FNameValue className;
            std::memcpy(&className,
                        static_cast<const uint8_t*>(klass) + 0x18,
                        sizeof(className));
            if (className.ComparisonIndex == kBoolPropertyClassNameIndex && className.Number == 0)
            {
                WriteAt(buffer, 0x70, kBoolFieldSize);
                WriteAt(buffer, 0x71, kBoolByteOffset);
                WriteAt(buffer, 0x72, kBoolByteMask);
                WriteAt(buffer, 0x73, kBoolFieldMask);
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

    struct LifecycleFixture
    {
        std::array<uint8_t, 0xb0> Function{};
        std::array<uint8_t, 0x80> PropertyA{};
        std::array<uint8_t, 0x80> PropertyB{};
        std::array<uint8_t, 0x80> PropertyC{};
        std::array<uint8_t, 0x80> PropertyD{};
        std::array<uint8_t, 0x80> PropertyE{};
        std::array<uint8_t, 0x40> ObjectPropertyClass{};
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
            Context.Regions.push_back({ObjectPropertyClass.data(), ObjectPropertyClass.size()});
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

    void InitClasses(LifecycleFixture& fixture)
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
        WriteObject(fixture.FunctionClass, kFunctionClassNameIndex, kFunctionClassObjectIndex, nullptr, nullptr);
    }

    void BuildFunction(LifecycleFixture& fixture,
                       int32_t functionNameIndex,
                       uint16_t numParms,
                       uint16_t parmsSize,
                       uint16_t returnValueOffset,
                       const std::array<FieldDef, 5>& fields)
    {
        InitClasses(fixture);
        WriteObject(fixture.Outer, kShooterGameModeNameIndex, kShooterGameModeObjectIndex, nullptr, nullptr);
        WriteObject(fixture.Function,
                    functionNameIndex,
                    functionNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());

        std::array<std::array<uint8_t, 0x80>*, 5> properties{
            &fixture.PropertyA,
            &fixture.PropertyB,
            &fixture.PropertyC,
            &fixture.PropertyD,
            &fixture.PropertyE,
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
        WriteAt(fixture.Function, 0x90, kLifecycleFunctionFlags);
        WriteAt(fixture.Function, 0x96, numParms);
        WriteAt(fixture.Function, 0x98, parmsSize);
        WriteAt(fixture.Function, 0x9a, returnValueOffset);
    }

    void BuildHandleNewPlayer(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kNewPlayerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kPlayerDataNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kPlayerCharacterNameIndex, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBIsFromLoginNameIndex, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kReturnValueNameIndex, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildOnLogout(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kOnLogoutNameIndex,
                      1,
                      0x08,
                      0xffff,
                      {{
                          {kExitingNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {},
                          {},
                          {},
                          {},
                      }});
    }

    void RequireFieldMetadata(const PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field,
                              PlayerPrincipalLifecycleReflection::LifecycleField expectedField,
                              int32_t expectedNameIndex,
                              int32_t expectedOffset,
                              size_t expectedSize,
                              bool expectedExposesRange,
                              bool expectedRedacted)
    {
        Require(field.Field == expectedField, "lifecycle field kind mismatch");
        Require(field.PropertyNameIndex == expectedNameIndex, "lifecycle field FName mismatch");
        Require(field.Offset == expectedOffset, "lifecycle field offset mismatch");
        Require(field.Size == expectedSize, "lifecycle field size mismatch");
        Require(field.ExposesRange == expectedExposesRange, "lifecycle field exposure mismatch");
        Require(field.Redacted == expectedRedacted, "lifecycle field redaction mismatch");
    }

    void TestRecognizesHandleNewPlayerWithOnlyBoolRanges()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer,
                "HandleNewPlayer kind mismatch");
        Require(invocation.FunctionNameIndex == kHandleNewPlayerNameIndex, "HandleNewPlayer FName mismatch");
        Require(invocation.OuterNameIndex == kShooterGameModeNameIndex, "HandleNewPlayer outer mismatch");
        Require(invocation.HasParameterRanges, "HandleNewPlayer missing parameter ranges");
        Require(invocation.Fields.size() == 5, "HandleNewPlayer field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                             kNewPlayerNameIndex,
                             0x00,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[0].Range.Data == nullptr, "NewPlayer range should be redacted");
        RequireFieldMetadata(invocation.Fields[3],
                             PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
                             kBIsFromLoginNameIndex,
                             0x18,
                             0x01,
                             true,
                             false);
        Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x18,
                "bIsFromLogin range mismatch");
        RequireFieldMetadata(invocation.Fields[4],
                             PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                             kReturnValueNameIndex,
                             0x19,
                             0x01,
                             true,
                             false);
        Require(invocation.Fields[4].Range.Data == fixture.Params.data() + 0x19,
                "ReturnValue range mismatch");
    }

    void TestRecognizesOnLogoutAsRedactedOnly()
    {
        LifecycleFixture fixture;
        BuildOnLogout(fixture);

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::OnLogout,
                "OnLogout kind mismatch");
        Require(invocation.Fields.size() == 1, "OnLogout field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::Exiting,
                             kExitingNameIndex,
                             0x00,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[0].Range.Data == nullptr, "Exiting range should be redacted");
    }

    void TestMetadataOnlyDoesNotExposeObjectRanges()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 0;
        fixture.Params[0x19] = 1;

        MemoryReader reader = fixture.Reader();
        fixture.Context.Regions.pop_back();
        fixture.Context.Regions.push_back({fixture.Params.data() + 0x18, 2});

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            reader,
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Fields[0].Range.Data == nullptr, "NewPlayer was read from params");
        Require(invocation.Fields[1].Range.Data == nullptr, "PlayerData was read from params");
        Require(invocation.Fields[2].Range.Data == nullptr, "PlayerCharacter was read from params");
        Require(invocation.Fields[3].Range.Data == fixture.Params.data() + 0x18,
                "bIsFromLogin narrow range mismatch");
        Require(invocation.Fields[4].Range.Data == fixture.Params.data() + 0x19,
                "ReturnValue narrow range mismatch");
    }

    void TestRejectsNonCanonicalBoolBytes()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 2;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "non-canonical bIsFromLogin was accepted");
        Require(invocation.FunctionNameIndex == -1, "rejected lifecycle invocation left stale function name");

        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 3;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "non-canonical ReturnValue was accepted");
        Require(invocation.Fields.empty(), "rejected lifecycle invocation left stale fields");
    }

    void TestRejectsWrongShapeAndOuter()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayer(fixture);
            WriteAt(fixture.Function, 0x98, uint16_t{0x1b});

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong HandleNewPlayer ParmsSize was accepted");
        }
        {
            LifecycleFixture fixture;
            BuildOnLogout(fixture);
            WriteObject(fixture.Outer, kShooterGameModeNameIndex + 1, kShooterGameModeObjectIndex, nullptr, nullptr);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "wrong OnLogout outer was accepted");
        }
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayer(fixture);
            const void* next = fixture.PropertyE.data();
            WriteAt(fixture.PropertyD, 0x28, next);
            WriteAt(fixture.PropertyE, 0x28, fixture.PropertyA.data());

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);
            Require(result.Status == ReadStatus::Implausible, "cyclic lifecycle property chain was accepted");
        }
    }

    void TestRejectsWrongBoolMetadata()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        WriteAt(fixture.PropertyD, 0x72, uint8_t{0xff});

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "wrong lifecycle bool metadata was accepted");
        Require(invocation.Fields.empty(), "rejected bool metadata left stale lifecycle fields");
    }

    void TestGateRejectsBeforeReading()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadOptions disabled = MakeReadOptionsForBinary(kSupportedShooterGameServerSha256, false);
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            disabled,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Disabled, "disabled lifecycle reflection was accepted");

        ReadOptions unsupported = MakeReadOptionsForBinary("not-this-binary", true);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            unsupported,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "unsupported lifecycle reflection was accepted");

        FieldLayout mutated = *FindSupportedLayout(kSupportedShooterGameServerSha256);
        mutated.UFunctionParmsSize = 0x99;
        ReadOptions wrongLayout;
        wrongLayout.Enabled = true;
        wrongLayout.Layout = &mutated;

        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            wrongLayout,
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::UnsupportedLayout, "mutated lifecycle layout was accepted");
    }
}

int main()
{
    TestRecognizesHandleNewPlayerWithOnlyBoolRanges();
    TestRecognizesOnLogoutAsRedactedOnly();
    TestMetadataOnlyDoesNotExposeObjectRanges();
    TestRejectsNonCanonicalBoolBytes();
    TestRejectsWrongShapeAndOuter();
    TestRejectsWrongBoolMetadata();
    TestGateRejectsBeforeReading();

    std::cout << "PlayerPrincipalLifecycleReflectionTests passed\n";
    return 0;
}
