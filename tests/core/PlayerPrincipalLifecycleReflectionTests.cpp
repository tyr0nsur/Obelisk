#include "ue/PlayerPrincipalLifecycleReflection.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace
{
    using namespace Obelisk::UE;
    using namespace Obelisk::UE::RuntimeReflection;

    constexpr int32_t kCheckJoinInProgressNameIndex = 1845;
    constexpr int32_t kHandleNewPlayerNameIndex = 2170;
    constexpr int32_t kOnLogoutNameIndex = 2384;
    constexpr int32_t kGameModeK2PostLoginNameIndex = 4943;
    constexpr int32_t kGameModeNameIndex = 9731;
    constexpr int32_t kGameModeObjectIndex = 405;
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
    constexpr int32_t kObservedRagnarokHandleNewPlayerName0 = 28418;
    constexpr int32_t kObservedRagnarokHandleNewPlayerName1 = 21314;
    constexpr int32_t kObservedRagnarokHandleNewPlayerName2 = 22968;
    constexpr int32_t kObservedRagnarokHandleNewPlayerName3 = 28516;
    constexpr int32_t kObservedRagnarokHandleNewPlayerName4 = 17724;
    constexpr int32_t kObservedRagnarokHandleNewPlayerPostRestartName0 = 28417;
    constexpr int32_t kObservedRagnarokHandleNewPlayerPostRestartName1 = 21313;
    constexpr int32_t kObservedRagnarokHandleNewPlayerPostRestartName2 = 22967;
    constexpr int32_t kObservedRagnarokHandleNewPlayerPostRestartName3 = 28515;
    constexpr int32_t kObservedRagnarokHandleNewPlayerPostRestartName4 = 17723;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260606Name0 = 28414;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260606Name1 = 21310;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260606Name2 = 22964;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260606Name3 = 28512;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260606Name4 = 17720;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260607Name0 = 28414;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260607Name1 = 21310;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260607Name2 = 22964;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260607Name3 = 28512;
    constexpr int32_t kObservedRagnarokHandleNewPlayerRestart20260607Name4 = 17719;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerObserved28416Name0 = 28416;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerObserved28416Name1 = 21312;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerObserved28416Name2 = 22966;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerObserved28416Name3 = 28514;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerObserved28416Name4 = 17722;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name0 = 28419;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name1 = 21315;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name2 = 22969;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name3 = 28517;
    constexpr int32_t kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name4 = 17725;
    constexpr int32_t kCurrentRuntimeHandleNewPlayerObservedName0 = 28422;
    constexpr int32_t kCurrentRuntimeHandleNewPlayerObservedName1 = 21318;
    constexpr int32_t kCurrentRuntimeHandleNewPlayerObservedName2 = 22972;
    constexpr int32_t kCurrentRuntimeHandleNewPlayerObservedName3 = 28520;
    constexpr int32_t kCurrentRuntimeHandleNewPlayerObservedName4 = 17727;
    constexpr int32_t kCurrentRuntimeK2PostLoginObservedName0 = 28422;
    constexpr int32_t kInferredRagnarokCheckJoinInProgressRestart20260606Name0 = 28512;
    constexpr int32_t kInferredRagnarokCheckJoinInProgressRestart20260606Name1 = 28414;
    constexpr int32_t kInferredRagnarokCheckJoinInProgressRestart20260606Name2 = 17721;
    constexpr int32_t kObservedRagnarokCheckJoinInProgressRestart20260607Name0 = 28512;
    constexpr int32_t kObservedRagnarokCheckJoinInProgressRestart20260607Name1 = 28414;
    constexpr int32_t kObservedRagnarokCheckJoinInProgressRestart20260607Name2 = 17719;
    constexpr int32_t kObservedRagnarokCheckJoinInProgressLive20260607Name2 = 17720;
    constexpr int32_t kObservedTheIslandCheckJoinInProgress20260607Name0 = 28520;
    constexpr int32_t kObservedTheIslandCheckJoinInProgress20260607Name1 = 28422;
    constexpr int32_t kObservedTheIslandCheckJoinInProgress20260607Name2 = 17729;
    constexpr int32_t kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name0 = 28514;
    constexpr int32_t kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name1 = 28416;
    constexpr int32_t kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name2 = 17723;
    constexpr int32_t kObservedRagnarokOnLogoutName0 = 28550;
    constexpr int32_t kObservedRagnarokOnLogoutPostRestartName0 = 28549;
    constexpr int32_t kObservedRagnarokOnLogoutRestart20260606Name0 = 28546;
    constexpr int32_t kCurrentRuntimeOnLogoutObservedName0 = 28554;
    constexpr int32_t kUnapprovedHandleNewPlayerDriftName0 = 30101;
    constexpr int32_t kUnapprovedOnLogoutDriftName0 = 30102;
    constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
    constexpr uint32_t kK2PostLoginFunctionFlags = 0x0c020800;
    constexpr uint32_t kCheckJoinInProgressFunctionFlags = 0x0c080c00;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint8_t kBoolFieldSize = 0x01;
    constexpr uint8_t kBoolByteOffset = 0x00;
    constexpr uint8_t kBoolByteMask = 0x01;
    constexpr uint8_t kBoolFieldMask = 0xff;
    constexpr size_t kMaxLifecycleDiagnosticReasonLength = 768;

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

    void RequireSafeDiagnosticReason(const std::string& reason)
    {
        Require(reason.size() <= kMaxLifecycleDiagnosticReasonLength, reason.c_str());
        Require(reason.find(' ') == std::string::npos, reason.c_str());
        Require(reason.find("0x") == std::string::npos, reason.c_str());
        Require(reason.find("params") == std::string::npos, reason.c_str());
        Require(reason.find("pointer") == std::string::npos, reason.c_str());
        Require(reason.find("identity") == std::string::npos, reason.c_str());
        Require(reason.find("class_object") == std::string::npos, reason.c_str());
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

    void BuildCheckJoinInProgress(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kBIsFromLoginNameIndex, 0x00, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kNewPlayerNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kReturnValueNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithReorderedPropertyChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kReturnValueNameIndex, 0x10, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {kNewPlayerNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBIsFromLoginNameIndex, 0x00, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithInferredRagnarokRestart20260606MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kInferredRagnarokCheckJoinInProgressRestart20260606Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kInferredRagnarokCheckJoinInProgressRestart20260606Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kInferredRagnarokCheckJoinInProgressRestart20260606Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithObservedRagnarokLive20260607MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressLive20260607Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithObservedTheIsland20260607MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kObservedTheIslandCheckJoinInProgress20260607Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kObservedTheIslandCheckJoinInProgress20260607Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kObservedTheIslandCheckJoinInProgress20260607Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithObservedRagnarokRestart20260607MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithMixedObservedRagnarokTheIsland20260607MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressRestart20260607Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kObservedTheIslandCheckJoinInProgress20260607Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithMixedCurrentRuntimeTheIslandRagnarokLive20260607MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kObservedTheIslandCheckJoinInProgress20260607Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kObservedTheIslandCheckJoinInProgress20260607Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kObservedRagnarokCheckJoinInProgressLive20260607Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildCheckJoinInProgressWithUnapprovedRagnarokLive20260607T150504MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kCheckJoinInProgressNameIndex,
                      3,
                      0x11,
                      0x10,
                      {{
                          {kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name0,
                           0x00,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolInputPropertyFlags},
                          {kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name1,
                           0x08,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name2,
                           0x10,
                           0x01,
                           fixture.BoolPropertyClass.data(),
                           kBoolReturnPropertyFlags},
                          {},
                          {},
                      }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
    }

    void BuildK2PostLogin(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kGameModeK2PostLoginNameIndex,
                      1,
                      0x08,
                      0xffff,
                      {{
                          {kNewPlayerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {},
                          {},
                          {},
                          {},
                      }});
        WriteObject(fixture.Outer, kGameModeNameIndex, kGameModeObjectIndex, nullptr, nullptr);
        WriteAt(fixture.Function, 0x90, kK2PostLoginFunctionFlags);
    }

    void BuildK2PostLoginWithCurrentRuntimeMismatch(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kGameModeK2PostLoginNameIndex,
                      1,
                      0x08,
                      0xffff,
                      {{
                          {kCurrentRuntimeK2PostLoginObservedName0,
                           0x00,
                           0x08,
                           fixture.ObjectPropertyClass.data(),
                           kObjectInputPropertyFlags},
                          {},
                          {},
                          {},
                          {},
                      }});
        WriteObject(fixture.Outer, kGameModeNameIndex, kGameModeObjectIndex, nullptr, nullptr);
        WriteAt(fixture.Function, 0x90, kK2PostLoginFunctionFlags);
    }

    void BuildHandleNewPlayerWithReorderedPropertyChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kReturnValueNameIndex, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {kNewPlayerNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kBIsFromLoginNameIndex, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kPlayerCharacterNameIndex, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kPlayerDataNameIndex, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithObservedRagnarokMismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kObservedRagnarokHandleNewPlayerName0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithObservedRagnarokPostRestartMismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kObservedRagnarokHandleNewPlayerPostRestartName0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerPostRestartName1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerPostRestartName2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerPostRestartName3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerPostRestartName4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithObservedRagnarokRestart20260606MismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kObservedRagnarokHandleNewPlayerRestart20260606Name0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260606Name1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260606Name2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260606Name3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260606Name4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithObservedRagnarokRestart20260607MismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kObservedRagnarokHandleNewPlayerRestart20260607Name0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260607Name1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260607Name2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260607Name3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerRestart20260607Name4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithUnapprovedRagnarokObserved28416MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kUnapprovedRagnarokHandleNewPlayerObserved28416Name0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerObserved28416Name1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerObserved28416Name2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerObserved28416Name3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerObserved28416Name4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithUnapprovedRagnarokPostRestartObserved28419MismatchChain(
        LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithCurrentRuntimeMismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kCurrentRuntimeHandleNewPlayerObservedName0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                      }});
    }

    void BuildHandleNewPlayerWithCurrentRuntimeIncompleteMismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      4,
                      0x1a,
                      0x19,
                      {{
                          {kCurrentRuntimeHandleNewPlayerObservedName0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kCurrentRuntimeHandleNewPlayerObservedName3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {},
                      }});
    }

    void BuildHandleNewPlayerWithReorderedObservedRagnarokMismatchChain(LifecycleFixture& fixture)
    {
        BuildFunction(fixture,
                      kHandleNewPlayerNameIndex,
                      5,
                      0x1a,
                      0x19,
                      {{
                          {kObservedRagnarokHandleNewPlayerName4, 0x19, 0x01, fixture.BoolPropertyClass.data(), kBoolReturnPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName0, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName3, 0x18, 0x01, fixture.BoolPropertyClass.data(), kBoolInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName2, 0x10, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
                          {kObservedRagnarokHandleNewPlayerName1, 0x08, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
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

    void BuildOnLogoutWithObservedRagnarokMismatchChain(
        LifecycleFixture& fixture,
        int32_t observedNameIndex = kObservedRagnarokOnLogoutName0)
    {
        BuildFunction(fixture,
                      kOnLogoutNameIndex,
                      1,
                      0x08,
                      0xffff,
                      {{
                          {observedNameIndex, 0x00, 0x08, fixture.ObjectPropertyClass.data(), kObjectInputPropertyFlags},
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

    void RequireCopiedBoolValue(const PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field,
                                uint8_t expected,
                                const char* message)
    {
        Require(field.HasCopiedBoolValue, message);
        Require(field.CopiedBoolValue == expected, message);
        Require(field.Range.Data == nullptr, message);
        Require(field.Range.Size == 0, message);
    }

    void RequireClearedInvocation(const PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation,
                                  const char* message)
    {
        Require(invocation.FunctionNameIndex == -1, message);
        Require(invocation.OuterNameIndex == -1, message);
        Require(!invocation.HasParameterRanges, message);
        Require(!invocation.PropertyNameIndicesMatched, message);
        Require(!invocation.PropertyFNameDriftDiagnosticOnly, message);
        Require(invocation.Fields.empty(), message);
        Require(invocation.PropertyFNameDrifts.empty(), message);
    }

    void RequireCurrentRuntimeOfflineSourceDiagnostic(const std::string& reason,
                                                      std::string_view target,
                                                      std::string_view expectedChain,
                                                      std::string_view observedChain)
    {
        Require(reason.find("diagnostic_current_runtime_unapproved_fname_drift") != std::string::npos,
                reason.c_str());
        Require(reason.find(
                    "offline_source_required_redacted_ufunction_snapshot_and_fname_manifest") !=
                    std::string::npos,
                reason.c_str());
        Require(reason.find("target_" + std::string(target)) != std::string::npos,
                reason.c_str());
        Require(reason.find("disposition_reject_only") != std::string::npos,
                reason.c_str());
        Require(reason.find("mismatch_delta_11") != std::string::npos,
                reason.c_str());
        Require(reason.find("expected_property_name_indices_" + std::string(expectedChain)) !=
                    std::string::npos,
                reason.c_str());
        Require(reason.find("observed_property_name_indices_" + std::string(observedChain)) !=
                    std::string::npos,
                reason.c_str());
        Require(reason.find("observed_property_fname_chain=" + std::string(observedChain)) !=
                    std::string::npos,
                reason.c_str());
        RequireSafeDiagnosticReason(reason);
    }

    void RequireObservedPropertyFNameChainNearStart(const std::string& reason,
                                                    std::string_view observedChain)
    {
        const std::string chainToken =
            "observed_property_fname_chain=" + std::string(observedChain);
        const size_t chainPosition = reason.find(chainToken);
        Require(chainPosition != std::string::npos, reason.c_str());
        Require(chainPosition < 256, reason.c_str());

        const size_t firstDetailedProperty = reason.find("prop_0_name_index");
        if (firstDetailedProperty != std::string::npos)
            Require(chainPosition < firstDetailedProperty, reason.c_str());

        RequireSafeDiagnosticReason(reason);
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
        Require(result.Reason.empty(), "exact HandleNewPlayer should not report FName drift");
        Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer,
                "HandleNewPlayer kind mismatch");
        Require(invocation.FunctionNameIndex == kHandleNewPlayerNameIndex, "HandleNewPlayer FName mismatch");
        Require(invocation.OuterNameIndex == kShooterGameModeNameIndex, "HandleNewPlayer outer mismatch");
        Require(invocation.HasParameterRanges, "HandleNewPlayer missing parameter ranges");
        Require(invocation.PropertyNameIndicesMatched, "HandleNewPlayer property FNames should match fixture");
        Require(!invocation.PropertyFNameDriftDiagnosticOnly,
                "HandleNewPlayer exact fixture reported diagnostic-only drift");
        Require(invocation.PropertyFNameDrifts.empty(), "HandleNewPlayer exact fixture recorded FName drift");
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
        RequireCopiedBoolValue(invocation.Fields[3], 1, "bIsFromLogin copied bool mismatch");
        RequireFieldMetadata(invocation.Fields[4],
                             PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                             kReturnValueNameIndex,
                             0x19,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[4], 1, "ReturnValue copied bool mismatch");
    }

    void TestRedactedObjectCorrelatesUseProcessLocalTokensNotRawPointers()
    {
        PlayerPrincipalLifecycleReflection::ResetProcessLocalSubjectTokensForTesting();

        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        const uintptr_t playerAddress = reinterpret_cast<uintptr_t>(fixture.Outer.data());
        WriteAt(fixture.Params, 0x00, playerAddress);
        WriteAt(fixture.Params, 0x08, playerAddress);
        WriteAt(fixture.Params, 0x10, reinterpret_cast<uintptr_t>(fixture.Function.data()));
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
        Require(invocation.Fields.size() == 5, "HandleNewPlayer token field count mismatch");
        Require(invocation.Fields[0].Range.Data == nullptr, "NewPlayer range should remain redacted");
        Require(invocation.Fields[1].Range.Data == nullptr, "PlayerData range should remain redacted");
        Require(invocation.Fields[2].Range.Data == nullptr, "PlayerCharacter range should remain redacted");

        const uint64_t playerToken = invocation.Fields[0].ProcessLocalSubjectToken;
        const uint64_t playerDataToken = invocation.Fields[1].ProcessLocalSubjectToken;
        const uint64_t characterToken = invocation.Fields[2].ProcessLocalSubjectToken;
        Require(playerToken != 0, "NewPlayer subject token missing");
        Require(playerDataToken == 0, "PlayerData should not retain a private subject token");
        Require(characterToken == 0, "PlayerCharacter should not retain a private subject token");
        Require(playerToken != static_cast<uint64_t>(playerAddress), "subject token leaked raw player pointer");

        PlayerPrincipalLifecycleReflection::LifecycleInvocation secondInvocation;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            secondInvocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(secondInvocation.Fields[0].ProcessLocalSubjectToken == playerToken,
                "same-process subject token should be stable for the same redacted object");
        Require(secondInvocation.Fields[1].ProcessLocalSubjectToken == 0,
                "same-process PlayerData token should remain unassigned");
        Require(secondInvocation.Fields[2].ProcessLocalSubjectToken == 0,
                "same-process PlayerCharacter token should remain unassigned");
    }

    void TestRecognitionCanSkipPrivateSubjectTokenAssignment()
    {
        PlayerPrincipalLifecycleReflection::ResetProcessLocalSubjectTokensForTesting();

        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        const uintptr_t playerAddress = reinterpret_cast<uintptr_t>(fixture.Outer.data());
        WriteAt(fixture.Params, 0x00, playerAddress);
        WriteAt(fixture.Params, 0x08, playerAddress);
        WriteAt(fixture.Params, 0x10, reinterpret_cast<uintptr_t>(fixture.Function.data()));
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation,
            PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::Skip);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Fields.size() == 5, "skip-token HandleNewPlayer field count mismatch");
        Require(invocation.Fields[0].ProcessLocalSubjectToken == 0,
                "skip-token recognition assigned NewPlayer private token");
        Require(invocation.Fields[1].ProcessLocalSubjectToken == 0,
                "skip-token recognition assigned PlayerData private token");
        Require(invocation.Fields[2].ProcessLocalSubjectToken == 0,
                "skip-token recognition assigned PlayerCharacter private token");
        Require(invocation.Fields[0].Range.Data == nullptr,
                "skip-token recognition exposed NewPlayer range");
        RequireCopiedBoolValue(invocation.Fields[3], 1,
                               "skip-token recognition lost bIsFromLogin copied bool");
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "skip-token recognition lost ReturnValue copied bool");

        PlayerPrincipalLifecycleReflection::LifecycleInvocation validated;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            validated,
            PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::ValidateOnly);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(validated.Fields[0].ProcessLocalSubjectToken == ~uint64_t{0},
                "validate-only recognition did not mark NewPlayer subject as validated");
        Require(validated.Fields[1].ProcessLocalSubjectToken == 0,
                "validate-only recognition assigned PlayerData private token");
        Require(validated.Fields[2].ProcessLocalSubjectToken == 0,
                "validate-only recognition assigned PlayerCharacter private token");

        PlayerPrincipalLifecycleReflection::LifecycleInvocation assigned;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            assigned);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(assigned.Fields[0].ProcessLocalSubjectToken != 0,
                "default recognition did not assign NewPlayer private token");
        Require(assigned.Fields[0].ProcessLocalSubjectToken != ~uint64_t{0},
                "default recognition returned the validate-only sentinel");
        Require(assigned.Fields[1].ProcessLocalSubjectToken == 0,
                "default recognition assigned PlayerData private token");
        Require(assigned.Fields[2].ProcessLocalSubjectToken == 0,
                "default recognition assigned PlayerCharacter private token");
    }

    void TestProcessLocalSubjectTokenSentinelsAreReserved()
    {
        PlayerPrincipalLifecycleReflection::ResetProcessLocalSubjectTokensForTesting();

        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        const uintptr_t firstAddress = reinterpret_cast<uintptr_t>(fixture.Outer.data());
        WriteAt(fixture.Params, 0x00, firstAddress);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::SetNextProcessLocalSubjectTokenForTesting(
            std::numeric_limits<uint64_t>::max() - 1);
        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Fields[0].ProcessLocalSubjectToken ==
                    std::numeric_limits<uint64_t>::max() - 1,
                "token allocator did not return the final assignable private token");
        Require(invocation.Fields[0].ProcessLocalSubjectToken != 0,
                "token allocator returned zero for final assignable token");
        Require(invocation.Fields[0].ProcessLocalSubjectToken != std::numeric_limits<uint64_t>::max(),
                "token allocator returned the validate-only sentinel");

        LifecycleFixture exhaustedFixture;
        BuildHandleNewPlayer(exhaustedFixture);
        const uintptr_t secondAddress = reinterpret_cast<uintptr_t>(exhaustedFixture.Outer.data());
        WriteAt(exhaustedFixture.Params, 0x00, secondAddress);
        exhaustedFixture.Params[0x18] = 1;
        exhaustedFixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation exhausted;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            exhaustedFixture.Reader(),
            Options(),
            exhaustedFixture.Function.data(),
            exhaustedFixture.Params.data(),
            exhausted);

        Require(result.Status == ReadStatus::OutOfBounds,
                "private token allocator did not fail closed after exhausting assignable tokens");
        Require(exhausted.Fields.empty(),
                "private token exhaustion left copied lifecycle fields");

        PlayerPrincipalLifecycleReflection::SetNextProcessLocalSubjectTokenForTesting(
            std::numeric_limits<uint64_t>::max());
        LifecycleFixture sentinelFixture;
        BuildHandleNewPlayer(sentinelFixture);
        const uintptr_t thirdAddress = reinterpret_cast<uintptr_t>(sentinelFixture.Outer.data());
        WriteAt(sentinelFixture.Params, 0x00, thirdAddress);
        sentinelFixture.Params[0x18] = 1;
        sentinelFixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation sentinel;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            sentinelFixture.Reader(),
            Options(),
            sentinelFixture.Function.data(),
            sentinelFixture.Params.data(),
            sentinel);

        Require(result.Status == ReadStatus::OutOfBounds,
                "private token allocator assigned the validate-only sentinel");
        Require(sentinel.Fields.empty(),
                "validate-only sentinel assignment left copied lifecycle fields");

        PlayerPrincipalLifecycleReflection::ResetProcessLocalSubjectTokensForTesting();
    }

    void TestRecognizesCheckJoinInProgressAsDiagnosticOnly()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgress(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.empty(), "exact CheckJoinInProgress reported diagnostic reason");
        Require(invocation.Function ==
                    PlayerPrincipalLifecycleReflection::LifecycleFunction::CheckJoinInProgressDiagnostic,
                "CheckJoinInProgress diagnostic kind mismatch");
        Require(invocation.FunctionNameIndex == kCheckJoinInProgressNameIndex,
                "CheckJoinInProgress FName mismatch");
        Require(invocation.OuterNameIndex == kShooterGameModeNameIndex,
                "CheckJoinInProgress outer mismatch");
        Require(invocation.PropertyNameIndicesMatched,
                "exact CheckJoinInProgress reported property FName drift");
        Require(!invocation.PropertyFNameDriftDiagnosticOnly,
                "exact CheckJoinInProgress marked drift diagnostic-only");
        Require(invocation.PropertyFNameDrifts.empty(),
                "exact CheckJoinInProgress retained drift records");
        Require(invocation.HasParameterRanges, "CheckJoinInProgress missing parameter ranges");
        Require(invocation.Fields.size() == 3, "CheckJoinInProgress field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
                             kBIsFromLoginNameIndex,
                             0x00,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[0],
                               1,
                               "CheckJoinInProgress bIsFromLogin copied bool mismatch");
        RequireFieldMetadata(invocation.Fields[1],
                             PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                             kNewPlayerNameIndex,
                             0x08,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[1].Range.Data == nullptr, "CheckJoinInProgress NewPlayer was exposed");
        RequireFieldMetadata(invocation.Fields[2],
                             PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                             kReturnValueNameIndex,
                             0x10,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[2],
                               0,
                               "CheckJoinInProgress ReturnValue copied bool mismatch");

        BuildCheckJoinInProgress(fixture);
        fixture.Params[0x00] = 2;
        fixture.Params[0x10] = 0;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "non-canonical CheckJoinInProgress bool was accepted");
        Require(invocation.Fields.empty(), "rejected CheckJoinInProgress left stale fields");

        BuildCheckJoinInProgress(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 2;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "non-canonical CheckJoinInProgress ReturnValue was accepted");
        Require(invocation.Fields.empty(),
                "rejected CheckJoinInProgress ReturnValue left stale fields");
    }

    void TestRejectsCheckJoinInProgressExactBoolTupleWithWrongPropertyOrder()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithReorderedPropertyChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "order-mismatched exact CheckJoinInProgress tuple was accepted");
        Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_lifecycle_property_offset_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "order-mismatched exact CheckJoinInProgress left copied output");
    }

    void TestCheckJoinInProgressDoesNotValidateRedactedNewPlayerPointer()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgress(fixture);
        fixture.Params[0x00] = 1;
        WriteAt(fixture.Params, 0x08, std::numeric_limits<uintptr_t>::max());
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function ==
                    PlayerPrincipalLifecycleReflection::LifecycleFunction::CheckJoinInProgressDiagnostic,
                "CheckJoinInProgress redacted-pointer fixture function mismatch");
        Require(invocation.Fields.size() == 3,
                "CheckJoinInProgress redacted-pointer fixture field count mismatch");
        RequireCopiedBoolValue(invocation.Fields[0],
                               1,
                               "CheckJoinInProgress redacted-pointer bIsFromLogin mismatch");
        RequireFieldMetadata(invocation.Fields[1],
                             PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                             kNewPlayerNameIndex,
                             0x08,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[1].Range.Data == nullptr,
                "CheckJoinInProgress redacted NewPlayer exposed a range");
        Require(invocation.Fields[1].ProcessLocalSubjectToken == 0,
                "CheckJoinInProgress redacted NewPlayer retained a subject token");
        RequireCopiedBoolValue(invocation.Fields[2],
                               0,
                               "CheckJoinInProgress redacted-pointer ReturnValue mismatch");
    }

    void TestRejectsInferredRagnarokCheckJoinInProgressFNameDrift()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithInferredRagnarokRestart20260606MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "inferred CheckJoinInProgress property FName drift was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("expected_name_index_17716") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_2_name_index_17721") != std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "inferred CheckJoinInProgress drift left copied output");
    }

    void TestAcceptsObservedRagnarokCheckJoinInProgressFNameDrift()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithObservedRagnarokRestart20260607MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28512") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_count_3") != std::string::npos,
                result.Reason.c_str());
        Require(!invocation.PropertyNameIndicesMatched,
                "observed CheckJoinInProgress drift reported exact property names");
        Require(invocation.PropertyFNameDrifts.size() == 3,
                "observed CheckJoinInProgress drift count mismatch");
        Require(invocation.Fields.size() == 3,
                "observed CheckJoinInProgress field count mismatch");
        Require(invocation.Fields[0].PropertyNameIndex ==
                    kObservedRagnarokCheckJoinInProgressRestart20260607Name0,
                "observed CheckJoinInProgress first property FName mismatch");
        Require(invocation.Fields[2].PropertyNameIndex ==
                    kObservedRagnarokCheckJoinInProgressRestart20260607Name2,
                "observed CheckJoinInProgress return property FName mismatch");
    }

    void TestAcceptsLiveObservedRagnarokCheckJoinInProgressFNameDrift()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithObservedRagnarokLive20260607MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 3,
                "live observed CheckJoinInProgress drift count mismatch");
        Require(invocation.Fields.size() == 3,
                "live observed CheckJoinInProgress field count mismatch");
        Require(invocation.Fields[2].PropertyNameIndex ==
                    kObservedRagnarokCheckJoinInProgressLive20260607Name2,
                "live observed CheckJoinInProgress return property FName mismatch");
    }

    void TestAcceptsObservedTheIslandCheckJoinInProgressFNameDrift()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithObservedTheIsland20260607MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 3,
                "TheIsland observed CheckJoinInProgress drift count mismatch");
        Require(invocation.Fields.size() == 3,
                "TheIsland observed CheckJoinInProgress field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
                             kObservedTheIslandCheckJoinInProgress20260607Name0,
                             0x00,
                             0x01,
                             true,
                             false);
        RequireFieldMetadata(invocation.Fields[2],
                             PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                             kObservedTheIslandCheckJoinInProgress20260607Name2,
                             0x10,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[0], 1,
                               "TheIsland CheckJoinInProgress bIsFromLogin copy mismatch");
        RequireCopiedBoolValue(invocation.Fields[2], 0,
                               "TheIsland CheckJoinInProgress ReturnValue copy mismatch");
    }

    void TestRejectsMixedObservedCheckJoinInProgressFNameDriftChain()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithMixedObservedRagnarokTheIsland20260607MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "mixed observed CheckJoinInProgress FName drift chain was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_unapproved_observed_property_FName_drift_chain") !=
                    std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireObservedPropertyFNameChainNearStart(result.Reason, "28512.28414.17729");
        RequireClearedInvocation(invocation,
                                 "mixed observed CheckJoinInProgress drift left copied output");
    }

    void TestRejectsMixedCurrentRuntimeCheckJoinInProgressFNameDriftChain()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithMixedCurrentRuntimeTheIslandRagnarokLive20260607MismatchChain(
            fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "mixed current-runtime CheckJoinInProgress FName drift chain was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_unapproved_observed_property_FName_drift_chain") !=
                    std::string::npos,
                result.Reason.c_str());
        RequireCurrentRuntimeOfflineSourceDiagnostic(
            result.Reason,
            "ShooterGameMode.CheckJoinInProgress",
            "28509.28411.17716",
            "28520.28422.17720");
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireClearedInvocation(
            invocation,
            "mixed current-runtime CheckJoinInProgress drift left copied output");
    }

    void TestRejectsCurrentRagnarokCheckJoinInProgressName28514DiagnosticMismatch()
    {
        LifecycleFixture fixture;
        BuildCheckJoinInProgressWithUnapprovedRagnarokLive20260607T150504MismatchChain(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "Ragnarok CheckJoinInProgress observed 28514/28416/17723 FName drift was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch_expected_name_index_28509") !=
                    std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_unapproved_observed_property_FName") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("position_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("prop_0_name_index_28514") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_1_name_index_28416") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_2_name_index_17723") != std::string::npos,
                result.Reason.c_str());
        RequireObservedPropertyFNameChainNearStart(result.Reason,
                                                   "28514.28416.17723");
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "Ragnarok CheckJoinInProgress observed 28514/28416/17723 mismatch left copied output");
    }

    void TestRecognizesK2PostLoginAsMetadataOnlyDiagnostic()
    {
        LifecycleFixture fixture;
        BuildK2PostLogin(fixture);

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.Function ==
                    PlayerPrincipalLifecycleReflection::LifecycleFunction::K2PostLoginDiagnostic,
                "K2_PostLogin diagnostic kind mismatch");
        Require(invocation.FunctionNameIndex == kGameModeK2PostLoginNameIndex,
                "K2_PostLogin FName mismatch");
        Require(invocation.OuterNameIndex == kGameModeNameIndex,
                "K2_PostLogin outer mismatch");
        Require(invocation.HasParameterRanges, "K2_PostLogin missing parameter ranges");
        Require(invocation.Fields.size() == 1, "K2_PostLogin field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                             kNewPlayerNameIndex,
                             0x00,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[0].Range.Data == nullptr, "K2_PostLogin NewPlayer was exposed");

        BuildK2PostLogin(fixture);
        WriteObject(fixture.Outer, kGameModeNameIndex + 1, kGameModeObjectIndex, nullptr, nullptr);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "wrong K2_PostLogin outer was accepted");
        Require(invocation.Fields.empty(), "rejected K2_PostLogin outer left stale fields");

        BuildK2PostLogin(fixture);
        WriteAt(fixture.Function, 0x90, kLifecycleFunctionFlags);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible, "wrong K2_PostLogin flags were accepted");
        Require(invocation.Fields.empty(), "rejected K2_PostLogin flags left stale fields");
    }

    void TestRejectsDiagnosticOnlyPropertyFNameDrift()
    {
        {
            LifecycleFixture fixture;
            BuildCheckJoinInProgress(fixture);
            fixture.Params[0x00] = 1;
            fixture.Params[0x10] = 0;
            const FNameValue driftedName{kObservedRagnarokHandleNewPlayerName3, 0};
            WriteAt(fixture.PropertyA, 0x18, driftedName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "unapproved CheckJoinInProgress FName drift was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("expected_name_index_28509") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("prop_0_name_index_28516") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "unapproved CheckJoinInProgress drift left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildK2PostLogin(fixture);
            const FNameValue driftedName{kObservedRagnarokHandleNewPlayerName0, 0};
            WriteAt(fixture.PropertyA, 0x18, driftedName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "K2_PostLogin diagnostic-only FName drift was accepted");
            Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("cause_lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("expected_name_28411") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("observed_name_28418") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "diagnostic-only K2_PostLogin drift left copied output");
        }
    }

    void TestRejectsHandleNewPlayerWithReorderedPropertyChain()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayerWithReorderedPropertyChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "reordered property chain was accepted");
        Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_lifecycle_property_offset_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("expected_name_28411") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_name_17716") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("expected_offset_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_offset_25") != std::string::npos, result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.FunctionNameIndex == -1, "rejected reordered chain left stale function name");
        Require(invocation.Fields.empty(), "rejected reordered chain left stale lifecycle fields");
    }

    template <typename Mutate>
    void RequireRejectsObservedHandleNewPlayerDriftMutation(Mutate mutate,
                                                            const char* acceptedMessage,
                                                            const char* reasonFragment,
                                                            const char* additionalReasonFragment = nullptr)
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        mutate(fixture);

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, acceptedMessage);
        Require(result.Reason.find(reasonFragment) != std::string::npos, result.Reason.c_str());
        if (additionalReasonFragment)
            Require(result.Reason.find(additionalReasonFragment) != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.FunctionNameIndex == -1,
                "rejected observed drift mutation left stale function name");
        Require(invocation.Fields.empty(), "rejected observed drift mutation left stale fields");
    }

    void TestAcceptsObservedRagnarokHandleNewPlayerFNameDriftWithExactShape()
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
        Require(result.Reason.empty(), "exact HandleNewPlayer should not report FName drift");
        Require(invocation.HasParameterRanges, "accepted HandleNewPlayer did not populate copied ranges");
        Require(invocation.PropertyNameIndicesMatched, "accepted HandleNewPlayer reported FName drift");
        Require(!invocation.PropertyFNameDriftDiagnosticOnly,
                "accepted exact HandleNewPlayer reported diagnostic-only drift");
        Require(invocation.PropertyFNameDrifts.empty(), "accepted HandleNewPlayer retained drift records");
        Require(invocation.Fields.size() == 5, "accepted HandleNewPlayer field count mismatch");
        RequireCopiedBoolValue(invocation.Fields[3], 1,
                               "accepted bIsFromLogin copied bool mismatch");
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "accepted ReturnValue copied bool mismatch");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("expected_name_index_28411") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28418") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("function_name_index_2170") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("outer_name_index_9755") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_count_5") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("drift_0_position_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("drift_0_delta_7") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("drift_4_delta_8") != std::string::npos, result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer,
                "observed HandleNewPlayer drift kind mismatch");
        Require(invocation.FunctionNameIndex == kHandleNewPlayerNameIndex,
                "observed HandleNewPlayer drift function FName mismatch");
        Require(invocation.OuterNameIndex == kShooterGameModeNameIndex,
                "observed HandleNewPlayer drift outer mismatch");
        Require(invocation.HasParameterRanges,
                "observed HandleNewPlayer drift did not populate copied bool ranges");
        Require(!invocation.PropertyNameIndicesMatched,
                "observed HandleNewPlayer drift reported exact property names");
        Require(invocation.PropertyFNameDriftDiagnosticOnly,
                "observed HandleNewPlayer drift was not marked diagnostic-only");
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "observed HandleNewPlayer drift count mismatch");
        Require(invocation.PropertyFNameDrifts[0].Position == 0,
                "observed HandleNewPlayer first drift position mismatch");
        Require(invocation.PropertyFNameDrifts[0].Field ==
                    PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                "observed HandleNewPlayer first drift field mismatch");
        Require(invocation.PropertyFNameDrifts[0].ExpectedNameIndex == kNewPlayerNameIndex,
                "observed HandleNewPlayer first drift expected FName mismatch");
        Require(invocation.PropertyFNameDrifts[0].ObservedNameIndex ==
                    kObservedRagnarokHandleNewPlayerName0,
                "observed HandleNewPlayer first drift observed FName mismatch");
        Require(invocation.PropertyFNameDrifts[4].Position == 4,
                "observed HandleNewPlayer return drift position mismatch");
        Require(invocation.PropertyFNameDrifts[4].ExpectedNameIndex == kReturnValueNameIndex,
                "observed HandleNewPlayer return drift expected FName mismatch");
        Require(invocation.PropertyFNameDrifts[4].ObservedNameIndex ==
                    kObservedRagnarokHandleNewPlayerName4,
                "observed HandleNewPlayer return drift observed FName mismatch");
        Require(invocation.Fields.size() == 5, "observed HandleNewPlayer drift field count mismatch");
        RequireFieldMetadata(invocation.Fields[0],
                             PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                             kObservedRagnarokHandleNewPlayerName0,
                             0x00,
                             0x08,
                             false,
                             true);
        Require(invocation.Fields[0].Range.Data == nullptr,
                "observed HandleNewPlayer drift exposed NewPlayer");
        RequireFieldMetadata(invocation.Fields[3],
                             PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
                             kObservedRagnarokHandleNewPlayerName3,
                             0x18,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[3], 1,
                               "observed HandleNewPlayer drift bIsFromLogin copied bool mismatch");
        RequireFieldMetadata(invocation.Fields[4],
                             PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                             kObservedRagnarokHandleNewPlayerName4,
                             0x19,
                             0x01,
                             true,
                             false);
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "observed HandleNewPlayer drift ReturnValue copied bool mismatch");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        const FNameValue permutedName{kPlayerDataNameIndex, 0};
        WriteAt(fixture.PropertyA, 0x18, permutedName);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "HandleNewPlayer drift to another lifecycle property name was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.Fields.empty(), "rejected lifecycle property name permutation left fields");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        WriteAt(fixture.PropertyD, 0x4c, int32_t{0x17});
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "observed FName drift with wrong shape was accepted");
        Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(invocation.Fields.empty(), "rejected observed wrong shape left stale fields");

        BuildHandleNewPlayerWithObservedRagnarokPostRestartMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28417") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_0_delta_6") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("drift_4_delta_7") != std::string::npos, result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "post-restart observed HandleNewPlayer drift count mismatch");
        Require(invocation.Fields[0].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerPostRestartName0,
                "post-restart observed HandleNewPlayer first property FName mismatch");
        Require(invocation.Fields[4].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerPostRestartName4,
                "post-restart observed HandleNewPlayer return property FName mismatch");

        BuildHandleNewPlayerWithObservedRagnarokRestart20260606MismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28414") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_0_delta_3") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("drift_4_delta_4") != std::string::npos, result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "2026-06-06 observed HandleNewPlayer drift count mismatch");
        Require(invocation.Fields[0].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerRestart20260606Name0,
                "2026-06-06 observed HandleNewPlayer first property FName mismatch");
        Require(invocation.Fields[4].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerRestart20260606Name4,
                "2026-06-06 observed HandleNewPlayer return property FName mismatch");

        BuildHandleNewPlayerWithObservedRagnarokRestart20260607MismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28414") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_4_delta_3") != std::string::npos, result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "2026-06-07 observed HandleNewPlayer drift count mismatch");
        Require(invocation.Fields[0].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerRestart20260607Name0,
                "2026-06-07 observed HandleNewPlayer first property FName mismatch");
        Require(invocation.Fields[4].PropertyNameIndex ==
                    kObservedRagnarokHandleNewPlayerRestart20260607Name4,
                "2026-06-07 observed HandleNewPlayer return property FName mismatch");

        BuildHandleNewPlayerWithCurrentRuntimeMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("observed_name_index_28422") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_0_delta_11") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("drift_4_delta_11") != std::string::npos,
                result.Reason.c_str());
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "current runtime observed HandleNewPlayer drift count mismatch");
        Require(invocation.Fields[0].PropertyNameIndex ==
                    kCurrentRuntimeHandleNewPlayerObservedName0,
                "current runtime observed HandleNewPlayer first property FName mismatch");
        Require(invocation.Fields[4].PropertyNameIndex ==
                    kCurrentRuntimeHandleNewPlayerObservedName4,
                "current runtime observed HandleNewPlayer return property FName mismatch");

        BuildHandleNewPlayerWithObservedRagnarokRestart20260606MismatchChain(fixture);
        const FNameValue mixedPostRestartName{kObservedRagnarokHandleNewPlayerPostRestartName0, 0};
        WriteAt(fixture.PropertyA, 0x18, mixedPostRestartName);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "mixed 2026-06-06 observed HandleNewPlayer drift variants were accepted");
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        Require(invocation.Fields.empty(), "mixed 2026-06-06 observed drift variants left stale fields");

        BuildHandleNewPlayerWithObservedRagnarokPostRestartMismatchChain(fixture);
        const FNameValue mixedVariantName{kObservedRagnarokHandleNewPlayerName0, 0};
        WriteAt(fixture.PropertyA, 0x18, mixedVariantName);
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(result.Status == ReadStatus::Implausible,
                "mixed observed HandleNewPlayer drift variants were accepted");
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        Require(invocation.Fields.empty(), "mixed observed drift variants left stale fields");
    }

    void TestAcceptedFNameDriftResetsBeforeSubsequentExactMatch()
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
        Require(invocation.PropertyNameIndicesMatched, "exact match reported drift before reset");
        Require(!invocation.PropertyFNameDriftDiagnosticOnly,
                "exact match reported diagnostic-only drift before reset");
        Require(invocation.PropertyFNameDrifts.empty(), "exact match recorded drift before reset");
        Require(invocation.Fields.size() == 5, "exact match field count mismatch before reset");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(!invocation.PropertyNameIndicesMatched,
                "observed drift after exact match reported exact property names");
        Require(invocation.PropertyFNameDriftDiagnosticOnly,
                "observed drift after exact match was not marked diagnostic-only");
        Require(invocation.PropertyFNameDrifts.size() == 5,
                "observed drift after exact match did not record drift metadata");
        Require(invocation.Fields.size() == 5, "observed drift after exact match lost lifecycle fields");
        Require(invocation.Fields[0].PropertyNameIndex == kObservedRagnarokHandleNewPlayerName0,
                "observed drift after exact match kept stale exact property name");
        RequireCopiedBoolValue(invocation.Fields[3], 1,
                               "observed drift after exact match bIsFromLogin copied bool mismatch");
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "observed drift after exact match ReturnValue copied bool mismatch");

        BuildHandleNewPlayer(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(static_cast<bool>(result), result.Reason.c_str());
        Require(invocation.PropertyNameIndicesMatched, "exact match kept stale drift match state");
        Require(!invocation.PropertyFNameDriftDiagnosticOnly,
                "exact match kept stale diagnostic-only drift state");
        Require(invocation.PropertyFNameDrifts.empty(), "exact match kept stale drift records");
        Require(invocation.Fields.size() == 5, "exact match lost lifecycle fields after drift reset");
        RequireCopiedBoolValue(invocation.Fields[3], 1,
                               "exact match bIsFromLogin copied bool mismatch after drift reset");
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "exact match ReturnValue copied bool mismatch after drift reset");
    }

    void TestRejectsCurrentRagnarokHandleNewPlayerName28416DiagnosticMismatch()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayerWithUnapprovedRagnarokObserved28416MismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "Ragnarok HandleNewPlayer observed 28416 FName drift was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch_expected_name_index_28411") !=
                    std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_unapproved_observed_property_FName") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("position_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("prop_0_name_index_28416") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_0_offset_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("prop_0_size_8") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("prop_0_class_name_index_5") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_1_name_index_21312") != std::string::npos,
                result.Reason.c_str());
        RequireObservedPropertyFNameChainNearStart(
            result.Reason,
            "28416.21312.22966.28514.17722");
        Require(result.Reason.find("_truncated") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "Ragnarok HandleNewPlayer observed 28416 mismatch left copied output");
    }

    void TestRejectsPostRestartRagnarokHandleNewPlayerName28419DiagnosticMismatch()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayerWithUnapprovedRagnarokPostRestartObserved28419MismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "post-restart Ragnarok HandleNewPlayer observed 28419 FName drift was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch_expected_name_index_28411") !=
                    std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_unapproved_observed_property_FName") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("position_0") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("prop_0_name_index_28419") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_1_name_index_21315") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_2_name_index_22969") != std::string::npos,
                result.Reason.c_str());
        RequireObservedPropertyFNameChainNearStart(
            result.Reason,
            "28419.21315.22969.28517.17725");
        Require(result.Reason.find("_truncated") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(
            invocation,
            "post-restart Ragnarok HandleNewPlayer observed 28419 mismatch left copied output");
    }

    void TestCurrentRuntimeAnchorFNameDriftUsesSourceBoundShapeAndRejectsIncompleteHandleNewPlayer()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithCurrentRuntimeMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result),
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_name_index_28422") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_0_delta_11") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_4_delta_11") != std::string::npos,
                    result.Reason.c_str());
            Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer,
                    "current runtime HandleNewPlayer drift function mismatch");
            Require(invocation.PropertyFNameDriftDiagnosticOnly,
                    "current runtime HandleNewPlayer drift was not marked diagnostic-only");
            Require(invocation.PropertyFNameDrifts.size() == 5,
                    "current runtime HandleNewPlayer drift count mismatch");
            RequireFieldMetadata(invocation.Fields[0],
                                 PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
                                 kCurrentRuntimeHandleNewPlayerObservedName0,
                                 0x00,
                                 0x08,
                                 false,
                                 true);
            RequireFieldMetadata(invocation.Fields[4],
                                 PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
                                 kCurrentRuntimeHandleNewPlayerObservedName4,
                                 0x19,
                                 0x01,
                                 true,
                                 false);
            RequireCopiedBoolValue(invocation.Fields[3], 1,
                                   "current runtime HandleNewPlayer bIsFromLogin copy mismatch");
            RequireCopiedBoolValue(invocation.Fields[4], 1,
                                   "current runtime HandleNewPlayer ReturnValue copy mismatch");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithCurrentRuntimeMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            const FNameValue mixedOldApprovedName{kObservedRagnarokHandleNewPlayerName0, 0};
            WriteAt(fixture.PropertyA, 0x18, mixedOldApprovedName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "mixed current-runtime and older HandleNewPlayer drift chain was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "mixed current-runtime HandleNewPlayer drift left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithCurrentRuntimeMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            const FNameValue exactName{kNewPlayerNameIndex, 0};
            WriteAt(fixture.PropertyA, 0x18, exactName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "partial exact/current-runtime HandleNewPlayer drift chain was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "partial current-runtime HandleNewPlayer drift left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildK2PostLoginWithCurrentRuntimeMismatch(fixture);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "current runtime K2_PostLogin 28422 FName drift was accepted");
            Require(result.Reason.find("lifecycle_property_validation_mismatch") !=
                        std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("cause_lifecycle_property_FName_mismatch") !=
                        std::string::npos,
                    result.Reason.c_str());
            RequireCurrentRuntimeOfflineSourceDiagnostic(
                result.Reason,
                "GameMode.K2_PostLogin",
                "28411",
                "28422");
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireClearedInvocation(invocation,
                                     "current runtime K2_PostLogin drift left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildOnLogoutWithObservedRagnarokMismatchChain(fixture,
                                                           kCurrentRuntimeOnLogoutObservedName0);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result),
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_name_index_28554") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_0_delta_11") != std::string::npos,
                    result.Reason.c_str());
            Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::OnLogout,
                    "current runtime OnLogout drift function mismatch");
            Require(invocation.PropertyFNameDriftDiagnosticOnly,
                    "current runtime OnLogout drift was not marked diagnostic-only");
            Require(invocation.PropertyFNameDrifts.size() == 1,
                    "current runtime OnLogout drift count mismatch");
            RequireFieldMetadata(invocation.Fields[0],
                                 PlayerPrincipalLifecycleReflection::LifecycleField::Exiting,
                                 kCurrentRuntimeOnLogoutObservedName0,
                                 0x00,
                                 0x08,
                                 false,
                                 true);
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "current runtime OnLogout drift exposed Exiting identity");
        }
    }

    void TestDiagnosticFNameMismatchPreservesCompactObservedPropertyChain()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithCurrentRuntimeIncompleteMismatchChain(fixture);
            fixture.Params[0x18] = 1;

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "incomplete current-runtime HandleNewPlayer-like chain was accepted");
            Require(result.Reason.find("lifecycle_function_shape_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_num_parms_4") != std::string::npos,
                    result.Reason.c_str());
            RequireObservedPropertyFNameChainNearStart(
                result.Reason,
                "28422.21318.22972.28520");
            Require(result.Reason.find("observed_property_fname_chain=28422.21318.22972.28520.17727") ==
                        std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireClearedInvocation(invocation,
                                     "incomplete current-runtime HandleNewPlayer-like chain left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithCurrentRuntimeIncompleteMismatchChain(fixture);
            fixture.Params[0x18] = 1;

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "incomplete current-runtime HandleNewPlayer-like chain was accepted");
            Require(result.Reason.find("lifecycle_function_shape_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_num_parms_4") != std::string::npos,
                    result.Reason.c_str());
            RequireObservedPropertyFNameChainNearStart(
                result.Reason,
                "28422.21318.22972.28520");
            Require(result.Reason.find("observed_property_fname_chain=28422.21318.22972.28520.17727") ==
                        std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireClearedInvocation(invocation,
                                     "incomplete current-runtime HandleNewPlayer-like chain left copied output");
        }
    }

    void TestRejectsUnapprovedLifecyclePropertyFNameDriftWithExactShape()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            const FNameValue unapprovedName{kUnapprovedHandleNewPlayerDriftName0, 0};
            WriteAt(fixture.PropertyA, 0x18, unapprovedName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "unapproved HandleNewPlayer property FName drift with exact shape was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "unapproved HandleNewPlayer property FName drift left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            const FNameValue exactName{kNewPlayerNameIndex, 0};
            WriteAt(fixture.PropertyA, 0x18, exactName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "mixed exact and observed HandleNewPlayer property FName chain was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "mixed exact and observed HandleNewPlayer property FName chain left output");
        }

        {
            LifecycleFixture fixture;
            BuildOnLogoutWithObservedRagnarokMismatchChain(fixture);
            const FNameValue unapprovedName{kUnapprovedOnLogoutDriftName0, 0};
            WriteAt(fixture.PropertyA, 0x18, unapprovedName);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "unapproved OnLogout property FName drift with exact shape was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "unapproved OnLogout property FName drift left copied output");
        }
    }

    void TestRejectsDuplicateObservedPropertyFNameDriftAndClearsCopiedOutput()
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
        Require(invocation.Fields.size() == 5, "exact match did not seed stale fields");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        const FNameValue duplicateName{kObservedRagnarokHandleNewPlayerName0, 0};
        WriteAt(fixture.PropertyB, 0x18, duplicateName);

        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "duplicate observed lifecycle property FName drift was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_0_name_index_28418") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("prop_1_name_index_28418") != std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "duplicate observed lifecycle property FName left stale copied output");
    }

    void TestRejectsWrongFNameNumbersAndClearsCopiedOutput()
    {
        {
            LifecycleFixture fixture;
            BuildOnLogoutWithObservedRagnarokMismatchChain(fixture);
            const FNameValue wrongNumber{kObservedRagnarokOnLogoutName0, 1};
            WriteAt(fixture.PropertyA, 0x18, wrongNumber);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "observed OnLogout drift with wrong property FName number was accepted");
            Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("prop_0_number_1") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "wrong OnLogout property FName number left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            WriteObject(fixture.Function,
                        kHandleNewPlayerNameIndex,
                        kHandleNewPlayerNameIndex,
                        fixture.FunctionClass.data(),
                        fixture.Outer.data(),
                        1);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "observed drift with wrong UFunction FName number was accepted");
            Require(result.Reason.find("lifecycle_function_shape_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("cause_UFunction_FName_does_not_match_lifecycle_spec") !=
                        std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "wrong UFunction FName number left copied output");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 1;
            WriteObject(fixture.Outer,
                        kShooterGameModeNameIndex,
                        kShooterGameModeObjectIndex,
                        nullptr,
                        nullptr,
                        1);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "observed drift with wrong outer FName number was accepted");
            Require(result.Reason.find("lifecycle_UFunction_outer_FName_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            RequireClearedInvocation(invocation,
                                     "wrong outer FName number left copied output");
        }
    }

    void TestRejectsObservedDriftWrongBoolMetadataWithMatchingOffsetsAndClearsCopiedOutput()
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
        Require(invocation.Fields.size() == 5, "exact match did not seed stale fields");
        Require(invocation.PropertyFNameDrifts.empty(), "exact match seeded stale drift records");

        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        WriteAt(fixture.PropertyD, 0x72, uint8_t{0xff});

        result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "observed FName drift with wrong bool metadata and matching offsets was accepted");
        Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_lifecycle_bool_property_metadata_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("expected_offset_24") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_offset_24") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("bool_byte_mask_255") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        RequireClearedInvocation(invocation,
                                 "wrong bool metadata observed drift left stale copied output");
    }

    void TestRejectsObservedRagnarokHandleNewPlayerFNameDriftMutations()
    {
        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteObject(fixture.Function,
                            kHandleNewPlayerNameIndex + 1,
                            kHandleNewPlayerNameIndex,
                            fixture.FunctionClass.data(),
                            fixture.Outer.data());
            },
            "observed FName drift with wrong function target was accepted",
            "UFunction_FName_index_is_not_a_supported_lifecycle_target");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteObject(fixture.FunctionClass,
                            kObjectPropertyClassNameIndex,
                            kFunctionClassObjectIndex,
                            nullptr,
                            nullptr);
            },
            "observed FName drift with wrong function class was accepted",
            "lifecycle_UFunction_class_FName_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteObject(fixture.Outer,
                            kShooterGameModeNameIndex + 1,
                            kShooterGameModeObjectIndex,
                            nullptr,
                            nullptr);
            },
            "observed FName drift with wrong function outer was accepted",
            "lifecycle_UFunction_outer_FName_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
            },
            "observed FName drift with wrong function flags was accepted",
            "lifecycle_function_shape_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                const void* nullNext = nullptr;
                WriteAt(fixture.Function, 0x96, uint16_t{4});
                WriteAt(fixture.PropertyD, 0x28, nullNext);
            },
            "observed FName drift with wrong NumParms was accepted",
            "lifecycle_function_shape_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.Function, 0x98, uint16_t{0x1b});
            },
            "observed FName drift with wrong ParmsSize was accepted",
            "lifecycle_function_shape_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.Function, 0x9a, uint16_t{0x18});
            },
            "observed FName drift with wrong ReturnValueOffset was accepted",
            "lifecycle_function_shape_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                const void* nullNext = nullptr;
                WriteAt(fixture.PropertyD, 0x28, nullNext);
            },
            "observed FName drift with missing property was accepted",
            "property_chain_ended_before_NumParms");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                BuildHandleNewPlayerWithReorderedObservedRagnarokMismatchChain(fixture);
            },
            "observed FName drift with reordered property shape was accepted",
            "cause_lifecycle_property_offset_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.PropertyA, 0x10, fixture.BoolPropertyClass.data());
            },
            "observed FName drift with wrong property class was accepted",
            "lifecycle_property_validation_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.PropertyD, 0x30, int32_t{2});
            },
            "observed FName drift with wrong property size was accepted",
            "cause_lifecycle_property_size_mismatch",
            "observed_array_dim_2");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.PropertyA, 0x30, int32_t{2});
                WriteAt(fixture.PropertyA, 0x34, int32_t{4});
            },
            "observed FName drift with wrong property ElementSize was accepted",
            "cause_lifecycle_property_ElementSize_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.PropertyD, 0x38, uint64_t{kBoolReturnPropertyFlags});
            },
            "observed FName drift with wrong property flags was accepted",
            "cause_lifecycle_property_flags_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                WriteAt(fixture.PropertyD, 0x72, uint8_t{0xff});
            },
            "observed FName drift with wrong bool metadata was accepted",
            "cause_lifecycle_bool_property_metadata_mismatch");

        RequireRejectsObservedHandleNewPlayerDriftMutation(
            [](LifecycleFixture& fixture) {
                const FNameValue name{kObservedRagnarokHandleNewPlayerName0, 1};
                WriteAt(fixture.PropertyA, 0x18, name);
            },
            "observed FName drift with wrong property FName number was accepted",
            "lifecycle_property_FName_mismatch");
    }

    void TestAcceptsObservedRagnarokOnLogoutFNameDriftWithExactShape()
    {
        for (const auto& [observedNameIndex, expectedDelta] :
             std::array<std::pair<int32_t, int32_t>, 3>{{
                 {kObservedRagnarokOnLogoutName0, 7},
                 {kObservedRagnarokOnLogoutPostRestartName0, 6},
                 {kObservedRagnarokOnLogoutRestart20260606Name0, 3},
             }})
        {
            LifecycleFixture fixture;
            BuildOnLogoutWithObservedRagnarokMismatchChain(fixture, observedNameIndex);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("expected_name_index_28543") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_name_index_" + std::to_string(observedNameIndex)) !=
                        std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("function_name_index_2384") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("outer_name_index_9755") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_count_1") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_0_position_0") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("drift_0_delta_" + std::to_string(expectedDelta)) !=
                        std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            Require(invocation.Function == PlayerPrincipalLifecycleReflection::LifecycleFunction::OnLogout,
                    "observed OnLogout drift kind mismatch");
            Require(invocation.FunctionNameIndex == kOnLogoutNameIndex,
                    "observed OnLogout drift function FName mismatch");
            Require(invocation.OuterNameIndex == kShooterGameModeNameIndex,
                    "observed OnLogout drift outer mismatch");
            Require(!invocation.PropertyNameIndicesMatched,
                    "observed OnLogout drift reported exact property names");
            Require(invocation.PropertyFNameDriftDiagnosticOnly,
                    "observed OnLogout drift was not marked diagnostic-only");
            Require(invocation.PropertyFNameDrifts.size() == 1,
                    "observed OnLogout drift count mismatch");
            Require(invocation.PropertyFNameDrifts[0].Position == 0,
                    "observed OnLogout drift position mismatch");
            Require(invocation.PropertyFNameDrifts[0].Field ==
                        PlayerPrincipalLifecycleReflection::LifecycleField::Exiting,
                    "observed OnLogout drift field mismatch");
            Require(invocation.PropertyFNameDrifts[0].ExpectedNameIndex == kExitingNameIndex,
                    "observed OnLogout drift expected FName mismatch");
            Require(invocation.PropertyFNameDrifts[0].ObservedNameIndex == observedNameIndex,
                    "observed OnLogout drift observed FName mismatch");
            Require(invocation.Fields.size() == 1, "observed OnLogout drift field count mismatch");
            RequireFieldMetadata(invocation.Fields[0],
                                 PlayerPrincipalLifecycleReflection::LifecycleField::Exiting,
                                 observedNameIndex,
                                 0x00,
                                 0x08,
                                 false,
                                 true);
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "observed OnLogout drift exposed Exiting identity");
        }

        LifecycleFixture fixture;
        BuildOnLogoutWithObservedRagnarokMismatchChain(fixture);
        WriteAt(fixture.PropertyA, 0x4c, int32_t{0x04});
        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);
        Require(!result,
                "observed OnLogout FName drift with wrong shape was accepted");
        Require(invocation.Fields.empty(), "rejected OnLogout wrong shape left stale fields");
    }

    void TestReportsPropertyValidationMismatchDiagnostics()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayer(fixture);
        WriteAt(fixture.PropertyD, 0x4c, int32_t{0x17});

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible, "wrong lifecycle property offset was accepted");
        Require(result.Reason.find("lifecycle_property_validation_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("cause_lifecycle_property_offset_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("expected_name_28509") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_name_28509") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("expected_offset_24") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_offset_23") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("expected_flags_69793219200") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_flags_69793219200") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("observed_class_name_3") != std::string::npos, result.Reason.c_str());
        Require(result.Reason.find("bool_byte_mask_1") != std::string::npos, result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.FunctionNameIndex == -1, "rejected property validation left stale function name");
        Require(invocation.Fields.empty(), "rejected property validation left stale lifecycle fields");
    }

    void TestBoundsLongDiagnosticReasons()
    {
        LifecycleFixture fixture;
        BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
        const FNameValue name{kObservedRagnarokHandleNewPlayerName0, 1};
        WriteAt(fixture.PropertyA, 0x18, name);

        PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
            fixture.Reader(),
            Options(),
            fixture.Function.data(),
            fixture.Params.data(),
            invocation);

        Require(result.Status == ReadStatus::Implausible,
                "long lifecycle diagnostic FName-number mismatch was accepted");
        Require(result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                result.Reason.c_str());
        Require(result.Reason.size() == kMaxLifecycleDiagnosticReasonLength,
                result.Reason.c_str());
        Require(result.Reason.compare(result.Reason.size() - 10, 10, "_truncated") == 0,
                result.Reason.c_str());
        RequireSafeDiagnosticReason(result.Reason);
        Require(invocation.FunctionNameIndex == -1, "long diagnostic rejection left stale function name");
        Require(invocation.Fields.empty(), "long diagnostic rejection left stale lifecycle fields");
    }

    void TestRedactsUnsafeLowerLevelDiagnosticReasons()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayer(fixture);
            WriteObject(fixture.BoolPropertyClass,
                        kBoolPropertyClassNameIndex,
                        kBoolPropertyClassObjectIndex + 1,
                        nullptr,
                        nullptr);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::Implausible,
                    "wrong lifecycle property class object index was accepted");
            Require(result.Reason.find("cause_lifecycle_reflection_rejected") != std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            Require(invocation.Fields.empty(), "rejected class-object diagnostic left stale lifecycle fields");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayer(fixture);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                nullptr,
                fixture.Params.data(),
                invocation);

            Require(result.Status == ReadStatus::InvalidArgument, "null lifecycle function was accepted");
            Require(result.Reason == "lifecycle_reflection_rejected", result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            Require(invocation.Fields.empty(), "rejected null-function diagnostic left stale lifecycle fields");
        }
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
        RequireCopiedBoolValue(invocation.Fields[3], 0,
                               "bIsFromLogin narrow copied bool mismatch");
        RequireCopiedBoolValue(invocation.Fields[4], 1,
                               "ReturnValue narrow copied bool mismatch");
    }

    void TestFNameDriftKeepsIdentityTextAndRawParamsUncopied()
    {
        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0x00] = 0xaa;
            fixture.Params[0x08] = 0xbb;
            fixture.Params[0x10] = 0xcc;
            fixture.Params[0x18] = 1;
            fixture.Params[0x19] = 0;

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
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(invocation.Fields.size() == 5, "observed drift field count mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "observed drift copied NewPlayer identity bytes");
            Require(invocation.Fields[1].Range.Data == nullptr,
                    "observed drift copied PlayerData identity bytes");
            Require(invocation.Fields[2].Range.Data == nullptr,
                    "observed drift copied PlayerCharacter identity bytes");
            RequireCopiedBoolValue(invocation.Fields[3], 1,
                                   "observed drift bIsFromLogin copied bool mismatch");
            RequireCopiedBoolValue(invocation.Fields[4], 0,
                                   "observed drift ReturnValue copied bool mismatch");
        }

        {
            LifecycleFixture fixture;
            BuildHandleNewPlayerWithObservedRagnarokMismatchChain(fixture);

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                nullptr,
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(!invocation.HasParameterRanges,
                    "observed drift without params reported copied parameter ranges");
            for (const auto& field : invocation.Fields)
            {
                Require(field.Range.Data == nullptr, "observed drift retained raw params without params");
                Require(field.Range.Size == 0, "observed drift retained raw param size without params");
            }
        }

        {
            LifecycleFixture fixture;
            BuildOnLogoutWithObservedRagnarokMismatchChain(fixture);
            fixture.Params[0] = 'p';
            fixture.Params[1] = 'l';
            fixture.Params[2] = 'a';
            fixture.Params[3] = 'y';
            fixture.Params[4] = 'e';
            fixture.Params[5] = 'r';

            PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            ReadResult result = PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                fixture.Reader(),
                Options(),
                fixture.Function.data(),
                fixture.Params.data(),
                invocation);

            Require(static_cast<bool>(result), result.Reason.c_str());
            Require(result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                    result.Reason.c_str());
            Require(invocation.Fields.size() == 1, "observed OnLogout drift field count mismatch");
            Require(invocation.Fields[0].Range.Data == nullptr,
                    "observed OnLogout drift copied text-like Exiting bytes");
            Require(invocation.Fields[0].Range.Size == 0,
                    "observed OnLogout drift retained text-like Exiting size");
        }
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
            Require(result.Reason.find("lifecycle_function_shape_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("cause_lifecycle_UFunction_ParmsSize_mismatch") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("expected_num_parms_5") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("observed_num_parms_5") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("expected_parms_size_26") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("observed_parms_size_27") != std::string::npos, result.Reason.c_str());
            Require(result.Reason.find("expected_return_value_offset_25") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_return_value_offset_25") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("expected_property_count_5") != std::string::npos,
                    result.Reason.c_str());
            Require(result.Reason.find("observed_property_count_5") != std::string::npos,
                    result.Reason.c_str());
            RequireSafeDiagnosticReason(result.Reason);
            Require(invocation.Fields.empty(), "rejected function shape left stale lifecycle fields");
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
    TestRedactedObjectCorrelatesUseProcessLocalTokensNotRawPointers();
    TestRecognitionCanSkipPrivateSubjectTokenAssignment();
    TestProcessLocalSubjectTokenSentinelsAreReserved();
    TestRecognizesCheckJoinInProgressAsDiagnosticOnly();
    TestRejectsCheckJoinInProgressExactBoolTupleWithWrongPropertyOrder();
    TestCheckJoinInProgressDoesNotValidateRedactedNewPlayerPointer();
    TestRejectsInferredRagnarokCheckJoinInProgressFNameDrift();
    TestAcceptsObservedRagnarokCheckJoinInProgressFNameDrift();
    TestAcceptsLiveObservedRagnarokCheckJoinInProgressFNameDrift();
    TestAcceptsObservedTheIslandCheckJoinInProgressFNameDrift();
    TestRejectsMixedObservedCheckJoinInProgressFNameDriftChain();
    TestRejectsMixedCurrentRuntimeCheckJoinInProgressFNameDriftChain();
    TestRejectsCurrentRagnarokCheckJoinInProgressName28514DiagnosticMismatch();
    TestRecognizesK2PostLoginAsMetadataOnlyDiagnostic();
    TestRejectsDiagnosticOnlyPropertyFNameDrift();
    TestRejectsHandleNewPlayerWithReorderedPropertyChain();
    TestAcceptsObservedRagnarokHandleNewPlayerFNameDriftWithExactShape();
    TestAcceptedFNameDriftResetsBeforeSubsequentExactMatch();
    TestRejectsCurrentRagnarokHandleNewPlayerName28416DiagnosticMismatch();
    TestRejectsPostRestartRagnarokHandleNewPlayerName28419DiagnosticMismatch();
    TestCurrentRuntimeAnchorFNameDriftUsesSourceBoundShapeAndRejectsIncompleteHandleNewPlayer();
    TestDiagnosticFNameMismatchPreservesCompactObservedPropertyChain();
    TestRejectsUnapprovedLifecyclePropertyFNameDriftWithExactShape();
    TestRejectsDuplicateObservedPropertyFNameDriftAndClearsCopiedOutput();
    TestRejectsWrongFNameNumbersAndClearsCopiedOutput();
    TestRejectsObservedDriftWrongBoolMetadataWithMatchingOffsetsAndClearsCopiedOutput();
    TestRejectsObservedRagnarokHandleNewPlayerFNameDriftMutations();
    TestAcceptsObservedRagnarokOnLogoutFNameDriftWithExactShape();
    TestReportsPropertyValidationMismatchDiagnostics();
    TestBoundsLongDiagnosticReasons();
    TestRedactsUnsafeLowerLevelDiagnosticReasons();
    TestRecognizesOnLogoutAsRedactedOnly();
    TestMetadataOnlyDoesNotExposeObjectRanges();
    TestFNameDriftKeepsIdentityTextAndRawParamsUncopied();
    TestRejectsNonCanonicalBoolBytes();
    TestRejectsWrongShapeAndOuter();
    TestRejectsWrongBoolMetadata();
    TestGateRejectsBeforeReading();

    std::cout << "PlayerPrincipalLifecycleReflectionTests passed\n";
    return 0;
}
