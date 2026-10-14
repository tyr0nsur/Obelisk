#include "hooks/ProcessEventPlayerPrincipalLifecycleObserver.h"

#include <atomic>
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace
{
    using namespace Obelisk::Hooks;
    using namespace Obelisk::UE::PlayerPrincipalLifecycleReflection;
    using namespace Obelisk::UE::RuntimeReflection;
    namespace Observer = ProcessEventPlayerPrincipalLifecycleObserver;

    constexpr const char* kSupportedSha =
        "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520";
    constexpr int32_t kCheckJoinInProgressNameIndex = 1845;
    constexpr int32_t kHandleNewPlayerNameIndex = 2170;
    constexpr int32_t kOnLogoutNameIndex = 2384;
    constexpr int32_t kGameModeK2PostLoginNameIndex = 4943;
    constexpr int32_t kGameModeNameIndex = 9731;
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
    constexpr int32_t kOnPostLoginDelegateNameIndex = 28545;
    constexpr int32_t kOnStartNewPlayerDelegateNameIndex = 28555;
    constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
    constexpr uint32_t kK2PostLoginFunctionFlags = 0x0c020800;
    constexpr uint32_t kCheckJoinInProgressFunctionFlags = 0x0c080c00;
    constexpr int32_t kGameModeObjectIndex = 405;
    constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
    constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
    constexpr uint8_t kBoolFieldSize = 0x01;
    constexpr uint8_t kBoolByteOffset = 0x00;
    constexpr uint8_t kBoolByteMask = 0x01;
    constexpr uint8_t kBoolFieldMask = 0xff;

    static_assert(std::is_standard_layout_v<Observer::LifecycleBoolObservation>,
                  "copied player lifecycle bool observations must keep a simple layout");
    static_assert(std::is_trivially_copyable_v<Observer::LifecycleBoolObservation>,
                  "copied player lifecycle bool observations must remain byte-copyable");
    static_assert(std::is_standard_layout_v<Observer::CopiedLifecycleObservation>,
                  "copied player lifecycle observations must keep a simple layout");
    static_assert(std::is_trivially_copyable_v<Observer::CopiedLifecycleObservation>,
                  "copied player lifecycle observations must remain byte-copyable");

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool ThrowingReader(const void*, size_t, void*)
    {
        throw std::runtime_error("reader should not be called");
    }

    Observer::Gate EnabledGate(const char* logLimit = "10", const char* dispatchLimit = "0")
    {
        return Observer::EvaluateGate("1", true, true, true, kSupportedSha, logLimit, dispatchLimit);
    }

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

    struct BudgetRaceReaderContext
    {
        std::vector<Region> Regions;
        const uint8_t* Params = nullptr;
        std::atomic<uint64_t>* Counter = nullptr;
        uint64_t Limit = 0;
        bool ExhaustBudgetOnMetadataRead = false;
        size_t MetadataReads = 0;
        size_t RedactedObjectParamReads = 0;
        size_t BoolParamReads = 0;
    };

    bool BudgetRaceReader(const void* address, size_t size, void* context)
    {
        auto* reader = static_cast<BudgetRaceReaderContext*>(context);
        const auto* ptr = static_cast<const uint8_t*>(address);
        bool isParamRead = false;
        if (reader->Params)
        {
            const auto* params = reader->Params;
            if ((ptr == params || ptr == params + 0x08 || ptr == params + 0x10) &&
                size == sizeof(uintptr_t))
            {
                isParamRead = true;
                ++reader->RedactedObjectParamReads;
            }
            if ((ptr == params + 0x18 || ptr == params + 0x19) && size == sizeof(uint8_t))
            {
                isParamRead = true;
                ++reader->BoolParamReads;
                if (reader->Counter)
                    reader->Counter->store(reader->Limit, std::memory_order_relaxed);
            }
        }
        if (!isParamRead && reader->ExhaustBudgetOnMetadataRead && reader->Counter)
        {
            ++reader->MetadataReads;
            reader->Counter->store(reader->Limit, std::memory_order_relaxed);
        }

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

    struct LifecycleReflectionFixture
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

    void InitClasses(LifecycleReflectionFixture& fixture)
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

    void BuildReflectedFunction(LifecycleReflectionFixture& fixture,
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

    void BuildCheckJoinInProgressFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kCheckJoinInProgressNameIndex,
                               3,
                               0x11,
                               0x10,
                               {{
                                   {kBIsFromLoginNameIndex,
                                    0x00,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kNewPlayerNameIndex,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kReturnValueNameIndex,
                                    0x10,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                                   {},
                                   {},
                               }});
        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildInferredCheckJoinInProgressRestart20260606Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildObservedCheckJoinInProgressRestart20260607Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildObservedCheckJoinInProgressLive20260607Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildObservedCheckJoinInProgressTheIsland20260607Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildMixedCurrentRuntimeCheckJoinInProgressTheIslandRagnarokLive20260607Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildUnapprovedCheckJoinInProgressLive20260607T150504Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12345000});
    }

    void BuildCurrentRuntimeK2PostLoginFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
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

    void BuildObservedHandleNewPlayerFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kObservedRagnarokHandleNewPlayerName0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildObservedHandleNewPlayerPostRestartFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kObservedRagnarokHandleNewPlayerPostRestartName0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerPostRestartName1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerPostRestartName2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerPostRestartName3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerPostRestartName4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildObservedHandleNewPlayerRestart20260606Function(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kObservedRagnarokHandleNewPlayerRestart20260606Name0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260606Name1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260606Name2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260606Name3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260606Name4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildObservedHandleNewPlayerRestart20260607Function(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kObservedRagnarokHandleNewPlayerRestart20260607Name0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260607Name1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260607Name2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260607Name3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerRestart20260607Name4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildUnapprovedHandleNewPlayerPostRestartObserved28419Function(
        LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildCurrentRuntimeHandleNewPlayerFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kCurrentRuntimeHandleNewPlayerObservedName0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kCurrentRuntimeHandleNewPlayerObservedName1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kCurrentRuntimeHandleNewPlayerObservedName2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kCurrentRuntimeHandleNewPlayerObservedName3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kCurrentRuntimeHandleNewPlayerObservedName4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
    }

    void BuildReorderedObservedHandleNewPlayerFunction(LifecycleReflectionFixture& fixture)
    {
        BuildReflectedFunction(fixture,
                               kHandleNewPlayerNameIndex,
                               5,
                               0x1a,
                               0x19,
                               {{
                                   {kObservedRagnarokHandleNewPlayerName4,
                                    0x19,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolReturnPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName0,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName3,
                                    0x18,
                                    0x01,
                                    fixture.BoolPropertyClass.data(),
                                    kBoolInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName2,
                                    0x10,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {kObservedRagnarokHandleNewPlayerName1,
                                    0x08,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                               }});
    }

    void BuildObservedOnLogoutFunction(
        LifecycleReflectionFixture& fixture,
        int32_t observedNameIndex = kObservedRagnarokOnLogoutName0)
    {
        BuildReflectedFunction(fixture,
                               kOnLogoutNameIndex,
                               1,
                               0x08,
                               0xffff,
                               {{
                                   {observedNameIndex,
                                    0x00,
                                    0x08,
                                    fixture.ObjectPropertyClass.data(),
                                    kObjectInputPropertyFlags},
                                   {},
                                   {},
                                   {},
                                   {},
                               }});
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
    }

    LifecycleFieldRange RedactedField(LifecycleField field,
                                      int32_t nameIndex,
                                      int32_t offset,
                                      size_t size,
                                      uint64_t processLocalSubjectToken = 0)
    {
        LifecycleFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = nameIndex;
        value.Offset = offset;
        value.Size = size;
        value.ExposesRange = false;
        value.Redacted = true;
        value.ProcessLocalSubjectToken = processLocalSubjectToken;
        return value;
    }

    LifecycleFieldRange BoolField(LifecycleField field, int32_t nameIndex, int32_t offset, const uint8_t* source)
    {
        LifecycleFieldRange value;
        value.Field = field;
        value.PropertyNameIndex = nameIndex;
        value.Offset = offset;
        value.Size = sizeof(uint8_t);
        value.ExposesRange = true;
        value.Redacted = false;
        value.HasCopiedBoolValue = true;
        value.CopiedBoolValue = source ? *source : 0;
        return value;
    }

    LifecycleInvocation HandleNewPlayerInvocation(uint8_t isFromLogin, uint8_t returnValue)
    {
        static uint8_t values[2] = {};
        values[0] = isFromLogin;
        values[1] = returnValue;

        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::HandleNewPlayer;
        invocation.FunctionNameIndex = kHandleNewPlayerNameIndex;
        invocation.OuterNameIndex = kShooterGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.PropertyNameIndicesMatched = true;
        invocation.Fields.push_back(RedactedField(LifecycleField::NewPlayer,
                                                 kNewPlayerNameIndex,
                                                 0x00,
                                                 0x08,
                                                 1));
        invocation.Fields.push_back(RedactedField(LifecycleField::PlayerData, kPlayerDataNameIndex, 0x08, 0x08));
        invocation.Fields.push_back(RedactedField(LifecycleField::PlayerCharacter,
                                                 kPlayerCharacterNameIndex,
                                                 0x10,
                                                 0x08));
        invocation.Fields.push_back(BoolField(LifecycleField::BIsFromLogin,
                                             kBIsFromLoginNameIndex,
                                             0x18,
                                             &values[0]));
        invocation.Fields.push_back(BoolField(LifecycleField::ReturnValue,
                                             kReturnValueNameIndex,
                                             0x19,
                                             &values[1]));
        return invocation;
    }

    LifecycleInvocation CheckJoinInProgressInvocation(uint8_t isFromLogin, uint8_t returnValue)
    {
        static uint8_t values[2] = {};
        values[0] = isFromLogin;
        values[1] = returnValue;

        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::CheckJoinInProgressDiagnostic;
        invocation.FunctionNameIndex = kCheckJoinInProgressNameIndex;
        invocation.OuterNameIndex = kShooterGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.PropertyNameIndicesMatched = true;
        invocation.Fields.push_back(BoolField(LifecycleField::BIsFromLogin,
                                             kBIsFromLoginNameIndex,
                                             0x00,
                                             &values[0]));
        invocation.Fields.push_back(RedactedField(LifecycleField::NewPlayer, kNewPlayerNameIndex, 0x08, 0x08));
        invocation.Fields.push_back(BoolField(LifecycleField::ReturnValue,
                                             kReturnValueNameIndex,
                                             0x10,
                                             &values[1]));
        return invocation;
    }

    LifecycleInvocation InferredRagnarokCheckJoinInProgressRestart20260606DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = CheckJoinInProgressInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex =
            kInferredRagnarokCheckJoinInProgressRestart20260606Name0;
        invocation.Fields[1].PropertyNameIndex =
            kInferredRagnarokCheckJoinInProgressRestart20260606Name1;
        invocation.Fields[2].PropertyNameIndex =
            kInferredRagnarokCheckJoinInProgressRestart20260606Name2;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kInferredRagnarokCheckJoinInProgressRestart20260606Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kInferredRagnarokCheckJoinInProgressRestart20260606Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kInferredRagnarokCheckJoinInProgressRestart20260606Name2,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokCheckJoinInProgressRestart20260607DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = CheckJoinInProgressInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex =
            kObservedRagnarokCheckJoinInProgressRestart20260607Name0;
        invocation.Fields[1].PropertyNameIndex =
            kObservedRagnarokCheckJoinInProgressRestart20260607Name1;
        invocation.Fields[2].PropertyNameIndex =
            kObservedRagnarokCheckJoinInProgressRestart20260607Name2;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokCheckJoinInProgressRestart20260607Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedRagnarokCheckJoinInProgressRestart20260607Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedRagnarokCheckJoinInProgressRestart20260607Name2,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokCheckJoinInProgressLive20260607DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = ObservedRagnarokCheckJoinInProgressRestart20260607DriftInvocation(
            isFromLogin,
            returnValue);
        invocation.Fields[2].PropertyNameIndex =
            kObservedRagnarokCheckJoinInProgressLive20260607Name2;
        invocation.PropertyFNameDrifts[2].ObservedNameIndex =
            kObservedRagnarokCheckJoinInProgressLive20260607Name2;
        return invocation;
    }

    LifecycleInvocation ObservedTheIslandCheckJoinInProgress20260607DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = CheckJoinInProgressInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex =
            kObservedTheIslandCheckJoinInProgress20260607Name0;
        invocation.Fields[1].PropertyNameIndex =
            kObservedTheIslandCheckJoinInProgress20260607Name1;
        invocation.Fields[2].PropertyNameIndex =
            kObservedTheIslandCheckJoinInProgress20260607Name2;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedTheIslandCheckJoinInProgress20260607Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedTheIslandCheckJoinInProgress20260607Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedTheIslandCheckJoinInProgress20260607Name2,
        });
        return invocation;
    }

    LifecycleInvocation MixedCurrentRuntimeCheckJoinInProgressTheIslandRagnarokLive20260607DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation =
            ObservedTheIslandCheckJoinInProgress20260607DriftInvocation(isFromLogin, returnValue);
        invocation.Fields[2].PropertyNameIndex =
            kObservedRagnarokCheckJoinInProgressLive20260607Name2;
        invocation.PropertyFNameDrifts[2].ObservedNameIndex =
            kObservedRagnarokCheckJoinInProgressLive20260607Name2;
        return invocation;
    }

    LifecycleInvocation UnapprovedRagnarokCheckJoinInProgressLive20260607T150504DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = CheckJoinInProgressInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex =
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name0;
        invocation.Fields[1].PropertyNameIndex =
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name1;
        invocation.Fields[2].PropertyNameIndex =
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name2;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kUnapprovedRagnarokCheckJoinInProgressLive20260607T150504Name2,
        });
        return invocation;
    }

    LifecycleInvocation K2PostLoginInvocation()
    {
        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::K2PostLoginDiagnostic;
        invocation.FunctionNameIndex = kGameModeK2PostLoginNameIndex;
        invocation.OuterNameIndex = kGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.PropertyNameIndicesMatched = true;
        invocation.Fields.push_back(RedactedField(LifecycleField::NewPlayer, kNewPlayerNameIndex, 0x00, 0x08));
        return invocation;
    }

    LifecycleInvocation CurrentRuntimeK2PostLoginDriftInvocation()
    {
        LifecycleInvocation invocation = K2PostLoginInvocation();
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kCurrentRuntimeK2PostLoginObservedName0;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kCurrentRuntimeK2PostLoginObservedName0,
        });
        return invocation;
    }

    LifecycleInvocation OnLogoutInvocation()
    {
        LifecycleInvocation invocation;
        invocation.Function = LifecycleFunction::OnLogout;
        invocation.FunctionNameIndex = kOnLogoutNameIndex;
        invocation.OuterNameIndex = kShooterGameModeNameIndex;
        invocation.HasParameterRanges = true;
        invocation.PropertyNameIndicesMatched = true;
        invocation.Fields.push_back(RedactedField(LifecycleField::Exiting,
                                                 kExitingNameIndex,
                                                 0x00,
                                                 0x08,
                                                 1));
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokHandleNewPlayerDriftInvocation(uint8_t isFromLogin,
                                                                       uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName0;
        invocation.Fields[1].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName1;
        invocation.Fields[2].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName2;
        invocation.Fields[3].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName3;
        invocation.Fields[4].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedRagnarokHandleNewPlayerName0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kObservedRagnarokHandleNewPlayerName1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kObservedRagnarokHandleNewPlayerName2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokHandleNewPlayerName3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedRagnarokHandleNewPlayerName4,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokHandleNewPlayerPostRestartDriftInvocation(uint8_t isFromLogin,
                                                                                  uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName0;
        invocation.Fields[1].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName1;
        invocation.Fields[2].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName2;
        invocation.Fields[3].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName3;
        invocation.Fields[4].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedRagnarokHandleNewPlayerPostRestartName0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kObservedRagnarokHandleNewPlayerPostRestartName1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kObservedRagnarokHandleNewPlayerPostRestartName2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokHandleNewPlayerPostRestartName3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedRagnarokHandleNewPlayerPostRestartName4,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokHandleNewPlayerRestart20260606DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260606Name0;
        invocation.Fields[1].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260606Name1;
        invocation.Fields[2].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260606Name2;
        invocation.Fields[3].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260606Name3;
        invocation.Fields[4].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260606Name4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260606Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260606Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260606Name2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260606Name3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260606Name4,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokHandleNewPlayerRestart20260607DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260607Name0;
        invocation.Fields[1].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260607Name1;
        invocation.Fields[2].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260607Name2;
        invocation.Fields[3].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260607Name3;
        invocation.Fields[4].PropertyNameIndex = kObservedRagnarokHandleNewPlayerRestart20260607Name4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260607Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260607Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260607Name2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260607Name3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kObservedRagnarokHandleNewPlayerRestart20260607Name4,
        });
        return invocation;
    }

    LifecycleInvocation UnapprovedRagnarokHandleNewPlayerPostRestartObserved28419DriftInvocation(
        uint8_t isFromLogin,
        uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex =
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name0;
        invocation.Fields[1].PropertyNameIndex =
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name1;
        invocation.Fields[2].PropertyNameIndex =
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name2;
        invocation.Fields[3].PropertyNameIndex =
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name3;
        invocation.Fields[4].PropertyNameIndex =
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kUnapprovedRagnarokHandleNewPlayerPostRestartObserved28419Name4,
        });
        return invocation;
    }

    LifecycleInvocation CurrentRuntimeHandleNewPlayerDriftInvocation(uint8_t isFromLogin,
                                                                     uint8_t returnValue)
    {
        LifecycleInvocation invocation = HandleNewPlayerInvocation(isFromLogin, returnValue);
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = kCurrentRuntimeHandleNewPlayerObservedName0;
        invocation.Fields[1].PropertyNameIndex = kCurrentRuntimeHandleNewPlayerObservedName1;
        invocation.Fields[2].PropertyNameIndex = kCurrentRuntimeHandleNewPlayerObservedName2;
        invocation.Fields[3].PropertyNameIndex = kCurrentRuntimeHandleNewPlayerObservedName3;
        invocation.Fields[4].PropertyNameIndex = kCurrentRuntimeHandleNewPlayerObservedName4;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::NewPlayer,
            kNewPlayerNameIndex,
            kCurrentRuntimeHandleNewPlayerObservedName0,
        });
        invocation.PropertyFNameDrifts.push_back({
            1,
            LifecycleField::PlayerData,
            kPlayerDataNameIndex,
            kCurrentRuntimeHandleNewPlayerObservedName1,
        });
        invocation.PropertyFNameDrifts.push_back({
            2,
            LifecycleField::PlayerCharacter,
            kPlayerCharacterNameIndex,
            kCurrentRuntimeHandleNewPlayerObservedName2,
        });
        invocation.PropertyFNameDrifts.push_back({
            3,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kCurrentRuntimeHandleNewPlayerObservedName3,
        });
        invocation.PropertyFNameDrifts.push_back({
            4,
            LifecycleField::ReturnValue,
            kReturnValueNameIndex,
            kCurrentRuntimeHandleNewPlayerObservedName4,
        });
        return invocation;
    }

    LifecycleInvocation ObservedRagnarokOnLogoutDriftInvocation(
        int32_t observedNameIndex = kObservedRagnarokOnLogoutName0)
    {
        LifecycleInvocation invocation = OnLogoutInvocation();
        invocation.PropertyNameIndicesMatched = false;
        invocation.Fields[0].PropertyNameIndex = observedNameIndex;
        invocation.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::Exiting,
            kExitingNameIndex,
            observedNameIndex,
        });
        return invocation;
    }

    LifecycleInvocation CurrentRuntimeOnLogoutDriftInvocation()
    {
        return ObservedRagnarokOnLogoutDriftInvocation(kCurrentRuntimeOnLogoutObservedName0);
    }

    void RequirePlayerPrincipalEventView(
        const Observer::CopiedLifecycleObservation& observation,
        Obelisk::Core::PlayerPrincipalEventKind expectedKind,
        Obelisk::Core::PlayerPrincipalAction expectedAction,
        size_t expectedBoolCount,
        const char* message)
    {
        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event), message);
        Require(event.Kind == expectedKind, message);
        Require(event.Action == expectedAction, message);
        Require(event.Bools.size() == expectedBoolCount, message);
        if (expectedBoolCount != 0)
            Require(event.Bools.data() == boolStorage.data(), message);
        else
            Require(event.Bools.empty(), message);
    }

    void RequireNoPlayerPrincipalEventView(
        const Observer::CopiedLifecycleObservation& observation,
        const char* message)
    {
        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(!Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event), message);
    }

    void RequireCurrentRuntimeOfflineSourceDiagnostic(const std::string& reason,
                                                      std::string_view target,
                                                      std::string_view expectedChain,
                                                      std::string_view observedChain)
    {
        Require(reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                reason.c_str());
        Require(reason.find("cause_unapproved_observed_property_FName") !=
                    std::string::npos ||
                    reason.find("lifecycle_property_validation_mismatch") !=
                        std::string::npos,
                reason.c_str());
        Require(reason.find("diagnostic_current_runtime_unapproved_fname_drift") !=
                    std::string::npos,
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
        Require(reason.find("observed_property_fname_chain=" + std::string(observedChain)) !=
                    std::string::npos,
                reason.c_str());
        Require(reason.find("observed_property_name_indices_" + std::string(observedChain)) !=
                    std::string::npos,
                reason.c_str());
    }

    std::string NormalizeDiagnosticReasonForSafetyCheck(std::string_view reason)
    {
        std::string normalized;
        normalized.reserve(reason.size());
        for (char ch : reason)
        {
            if (ch >= 'A' && ch <= 'Z')
                normalized.push_back(static_cast<char>(ch - 'A' + 'a'));
            else if ((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9'))
                normalized.push_back(ch);
        }
        return normalized;
    }

    void RequireNearMissReasonMetadataClassification(const std::string& reason,
                                                     const char* message)
    {
        constexpr size_t kMaxNearMissReasonLength = 512;
        Require(reason.size() <= kMaxNearMissReasonLength, message);
        Require(reason.find("metadata_only_true") != std::string::npos, message);
        Require(reason.find("identity_logged_false") != std::string::npos, message);
        Require(reason.find("evidence_claim_none") != std::string::npos, message);
        Require(reason.find("principal_claim_none") != std::string::npos, message);

        const std::string normalized = NormalizeDiagnosticReasonForSafetyCheck(reason);
        Require(normalized.find("params") == std::string::npos, message);
        Require(normalized.find("pointer") == std::string::npos, message);
        Require(normalized.find("classobject") == std::string::npos, message);
    }

    void RequireNearMissReasonCarriesEarlyPropertyChains(const std::string& reason,
                                                         std::string_view expectedChain,
                                                         std::string_view observedChain,
                                                         const char* message)
    {
        constexpr size_t kMaxCriticalPrefix = 360;
        const std::string expectedToken =
            "expected_property_name_indices_" + std::string(expectedChain);
        const std::string observedToken =
            "observed_property_name_indices_" + std::string(observedChain);
        const size_t expectedPos = reason.find(expectedToken);
        const size_t observedPos = reason.find(observedToken);
        Require(expectedPos != std::string::npos, message);
        Require(observedPos != std::string::npos, message);
        Require(expectedPos < observedPos, message);
        Require(observedPos + observedToken.size() <= kMaxCriticalPrefix, message);

        const size_t outerPos = reason.find("expected_outer_name_index_");
        Require(outerPos == std::string::npos || observedPos < outerPos, message);
    }

    void RequireNoDiagnosticObservationForAcceptedInvocation(const LifecycleInvocation& invocation,
                                                             const char* message)
    {
        Observer::CopiedLifecycleObservation diagnosticObservation;
        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(invocation, diagnosticObservation),
                message);
        Require(diagnosticObservation.BoolCount == 0, message);
        Require(diagnosticObservation.RedactedCount == 0, message);
        RequireNoPlayerPrincipalEventView(diagnosticObservation, message);
    }

    void RequireNoAcceptedObservationForDiagnosticInvocation(const LifecycleInvocation& invocation,
                                                             const char* message)
    {
        Observer::CopiedLifecycleObservation acceptedObservation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, acceptedObservation),
                message);
        Require(acceptedObservation.BoolCount == 0, message);
        Require(acceptedObservation.RedactedCount == 0, message);
        RequireNoPlayerPrincipalEventView(acceptedObservation, message);
    }

    void RequireCopiedEventView(
        const Observer::Attempt& attempt,
        Obelisk::Core::PlayerPrincipalEventKind expectedKind,
        Obelisk::Core::PlayerPrincipalAction expectedAction,
        size_t expectedBoolCount,
        const char* message)
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                message);
        RequirePlayerPrincipalEventView(observation,
                                        expectedKind,
                                        expectedAction,
                                        expectedBoolCount,
                                        message);
    }

    void TestGateMatrix()
    {
        Require(Observer::EvaluateGate(nullptr, true, true, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::Disabled,
                "missing enable should disable gate");
        Require(Observer::EvaluateGate("1", false, true, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingObserverDebugProfile,
                "missing observer profile accepted");
        Require(Observer::EvaluateGate("1", true, false, true, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingObserverDebugWindow,
                "missing observer window accepted");
        Require(Observer::EvaluateGate("1", true, true, false, kSupportedSha, "1", "0").Status ==
                    Observer::GateStatus::MissingInstanceMarker,
                "missing observer marker accepted");
        Require(Observer::EvaluateGate("1", true, true, true, nullptr, "1", "0").Status ==
                    Observer::GateStatus::MissingBinarySha256,
                "missing sha accepted");
        Require(Observer::EvaluateGate("1",
                                       true,
                                       true,
                                       true,
                                       "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                                       "1",
                                       "0")
                    .Status == Observer::GateStatus::UnsupportedBinarySha256,
                "unsupported sha accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, nullptr, "0").Status ==
                    Observer::GateStatus::MissingLogLimit,
                "missing log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "abc", "0").Status ==
                    Observer::GateStatus::MalformedLogLimit,
                "malformed log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "0", "0").Status ==
                    Observer::GateStatus::ZeroLogLimit,
                "zero log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "11", "0").Status ==
                    Observer::GateStatus::LogLimitTooLarge,
                "oversized log limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", nullptr).Status ==
                    Observer::GateStatus::MissingDispatchLimit,
                "missing dispatch limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", "x").Status ==
                    Observer::GateStatus::MalformedDispatchLimit,
                "malformed dispatch limit accepted");
        Require(Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", "1").Status ==
                    Observer::GateStatus::NonZeroDispatchLimit,
                "non-zero dispatch limit accepted");

        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "valid lifecycle gate not enabled");
        Require(gate.LogLimit == 10, "lifecycle log limit mismatch");
        Require(gate.DispatchLimit == 0, "lifecycle dispatch limit mismatch");
    }

    void TestNameAndBudgetPrefilters()
    {
        Require(Observer::IsReflectedLifecycleNameIndex(kHandleNewPlayerNameIndex),
                "HandleNewPlayer name index rejected");
        Require(Observer::IsReflectedLifecycleNameIndex(kOnLogoutNameIndex),
                "OnLogout name index rejected");
        Require(Observer::IsReflectedLifecycleNameIndex(kCheckJoinInProgressNameIndex),
                "CheckJoinInProgress rejected as reflected lifecycle");
        Require(!Observer::IsReflectedLifecycleNameIndex(9999), "non-lifecycle name index accepted");
        Require(!Observer::IsReflectedLifecycleNameIndex(kGameModeK2PostLoginNameIndex),
                "diagnostic-only K2_PostLogin accepted as reflected lifecycle");
        Require(!Observer::IsReflectedLifecycleNameIndex(kOnPostLoginDelegateNameIndex),
                "diagnostic-only OnPostLogin delegate accepted as reflected lifecycle");
        Require(!Observer::IsReflectedLifecycleNameIndex(kOnStartNewPlayerDelegateNameIndex),
                "diagnostic-only OnStartNewPlayer delegate accepted as reflected lifecycle");
        Require(!Observer::IsLifecycleDiagnosticCandidateNameIndex(kCheckJoinInProgressNameIndex),
                "CheckJoinInProgress reflected lifecycle target entered diagnostic candidate logging");
        Require(!Observer::IsLifecycleDiagnosticCandidateNameIndex(kHandleNewPlayerNameIndex),
                "HandleNewPlayer reflected lifecycle target entered diagnostic candidate logging");
        Require(!Observer::IsLifecycleDiagnosticCandidateNameIndex(kOnLogoutNameIndex),
                "OnLogout reflected lifecycle target entered diagnostic candidate logging");
        Require(Observer::IsLifecycleDiagnosticCandidateNameIndex(kGameModeK2PostLoginNameIndex),
                "K2_PostLogin diagnostic candidate rejected");
        Require(Observer::IsLifecycleDiagnosticCandidateNameIndex(kOnPostLoginDelegateNameIndex),
                "OnPostLogin diagnostic candidate rejected");
        Require(Observer::IsLifecycleDiagnosticCandidateNameIndex(kOnStartNewPlayerDelegateNameIndex),
                "OnStartNewPlayer diagnostic candidate rejected");
        Require(!Observer::IsLifecycleDiagnosticCandidateNameIndex(9999),
                "unknown diagnostic candidate accepted");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kCheckJoinInProgressNameIndex),
                    "ShooterGameMode.CheckJoinInProgress") == 0,
                "CheckJoinInProgress diagnostic target mismatch");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kHandleNewPlayerNameIndex),
                    "ShooterGameMode.HandleNewPlayer") == 0,
                "HandleNewPlayer diagnostic target mismatch");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kOnLogoutNameIndex),
                    "ShooterGameMode.OnLogout") == 0,
                "OnLogout diagnostic target mismatch");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kGameModeK2PostLoginNameIndex),
                    "GameMode.K2_PostLogin") == 0,
                "K2_PostLogin diagnostic target mismatch");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kOnPostLoginDelegateNameIndex),
                    "ShooterGameMode.OnPostLogin__DelegateSignature") == 0,
                "OnPostLogin diagnostic target mismatch");
        Require(std::strcmp(
                    Observer::LifecycleDiagnosticCandidateTargetName(kOnStartNewPlayerDelegateNameIndex),
                    "ShooterGameMode.OnStartNewPlayer__DelegateSignature") == 0,
                "OnStartNewPlayer diagnostic target mismatch");
        Require(std::strcmp(Observer::LifecycleDiagnosticCandidateTargetName(9999), "Unknown.Unknown") == 0,
                "unknown diagnostic target mismatch");

        std::atomic<uint64_t> counter{0};
        uint64_t number = 0;
        Require(Observer::TryReserveObservationBudget(counter, 2, number), "first reserve failed");
        Require(number == 1, "first reserve number mismatch");
        Require(Observer::TryReserveObservationBudget(counter, 2, number), "second reserve failed");
        Require(number == 2, "second reserve number mismatch");
        Require(!Observer::TryReserveObservationBudget(counter, 2, number), "budget overflow accepted");
        Require(number == 0, "budget overflow number was not cleared");
        Require(!Observer::ShouldLogObservation(0, 2), "zero observation was loggable");
        Require(Observer::ShouldLogObservation(2, 2), "bounded observation was not loggable");
        Require(!Observer::ShouldLogObservation(3, 2), "over-budget observation was loggable");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t dispatchNumber = 99;
        Require(!Observer::HasObservationBudgetRemaining(dispatchCounter, 0),
                "zero dispatch budget reported remaining capacity");
        Require(!Observer::TryReserveObservationBudget(dispatchCounter, 0, dispatchNumber),
                "zero dispatch budget reserved a callback/event slot");
        Require(dispatchNumber == 0, "zero dispatch budget left a dispatch sequence");
        Require(dispatchCounter.load(std::memory_order_relaxed) == 0,
                "zero dispatch budget incremented dispatch counter");
    }

    void TestTryIdentifyFastPathsDoNotRead()
    {
        MemoryReader reader{ThrowingReader, nullptr};
        Observer::Attempt attempt = Observer::TryIdentifyInvocation(
            {}, kHandleNewPlayerNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::Disabled, "disabled gate did not short-circuit");

        attempt = Observer::TryIdentifyInvocation(
            EnabledGate(), 9999, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "non-lifecycle FName did not short-circuit");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "non-lifecycle FName left a reflected lifecycle invocation");

        attempt = Observer::TryIdentifyInvocation(
            EnabledGate(), kCheckJoinInProgressNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "CheckJoinInProgress reflected lifecycle did not reach reflection reader");

        for (int32_t diagnosticOnlyNameIndex : {
                 kGameModeK2PostLoginNameIndex,
                 kOnPostLoginDelegateNameIndex,
                 kOnStartNewPlayerDelegateNameIndex,
             })
        {
            attempt = Observer::TryIdentifyInvocation(
                EnabledGate(), diagnosticOnlyNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
            Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                    "diagnostic-only lifecycle FName reached reflection reader");
            Require(attempt.Invocation.FunctionNameIndex == -1,
                    "diagnostic-only lifecycle FName left a reflected invocation");
        }

        attempt = Observer::TryIdentifyInvocation(
            EnabledGate(), kHandleNewPlayerNameIndex, reader, reinterpret_cast<void*>(0x10000), nullptr);
        Require(attempt.Status == Observer::AttemptStatus::Rejected, "reader exception was not rejected");
    }

    void TestFunctionFNameNearMissDiagnosticRemainsNonEvidence()
    {
        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        WriteObject(fixture.Function,
                    kHandleNewPlayerNameIndex + 500,
                    kHandleNewPlayerNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());

        Observer::FunctionFNameNearMissDiagnostic nearMiss;
        Require(Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                     kHandleNewPlayerNameIndex + 500,
                                                                     fixture.Reader(),
                                                                     fixture.Function.data(),
                                                                     nearMiss),
                "HandleNewPlayer-shaped function FName near miss was not diagnosed");
        Require(nearMiss.Function == LifecycleFunction::HandleNewPlayer,
                "near-miss function kind mismatch");
        Require(nearMiss.ExpectedFunctionNameIndex == kHandleNewPlayerNameIndex,
                "near-miss expected function FName mismatch");
        Require(nearMiss.ObservedFunctionNameIndex == kHandleNewPlayerNameIndex + 500,
                "near-miss observed function FName mismatch");
        Require(nearMiss.OuterNameIndex == kShooterGameModeNameIndex,
                "near-miss outer FName mismatch");
        Require(nearMiss.Result.Status == ReadStatus::Ok,
                "near-miss diagnostic did not report metadata-only success");
        Require(nearMiss.Result.Reason.find("lifecycle_function_FName_near_miss") !=
                    std::string::npos,
                "near-miss diagnostic reason missing marker");
        Require(nearMiss.Result.Reason.find("expected_name_index_2170") !=
                    std::string::npos,
                "near-miss diagnostic reason missing expected FName");
        RequireNearMissReasonMetadataClassification(
            nearMiss.Result.Reason,
            "near-miss diagnostic reason lost metadata-only classification");

        BuildObservedHandleNewPlayerFunction(fixture);
        WriteObject(fixture.Function,
                    kOnPostLoginDelegateNameIndex,
                    kOnPostLoginDelegateNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());
        Require(Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                     kOnPostLoginDelegateNameIndex,
                                                                     fixture.Reader(),
                                                                     fixture.Function.data(),
                                                                     nearMiss),
                "delegate-named HandleNewPlayer-shaped function near miss was not diagnosed");
        Require(nearMiss.Function == LifecycleFunction::HandleNewPlayer,
                "delegate near-miss function kind mismatch");
        Require(nearMiss.ExpectedFunctionNameIndex == kHandleNewPlayerNameIndex,
                "delegate near-miss expected function FName mismatch");
        Require(nearMiss.ObservedFunctionNameIndex == kOnPostLoginDelegateNameIndex,
                "delegate near-miss observed function FName mismatch");
        Require(nearMiss.Result.Status == ReadStatus::Ok,
                "delegate near-miss diagnostic did not report metadata-only success");
        RequireNearMissReasonMetadataClassification(
            nearMiss.Result.Reason,
            "delegate near-miss diagnostic reason lost metadata-only classification");

        BuildUnapprovedHandleNewPlayerPostRestartObserved28419Function(fixture);
        WriteObject(fixture.Function,
                    kHandleNewPlayerNameIndex + 600,
                    kHandleNewPlayerNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());
        Require(Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                     kHandleNewPlayerNameIndex + 600,
                                                                     fixture.Reader(),
                                                                     fixture.Function.data(),
                                                                     nearMiss),
                "unapproved-property HandleNewPlayer-shaped near miss was not diagnosed");
        Require(nearMiss.Function == LifecycleFunction::HandleNewPlayer,
                "unapproved-property near-miss function kind mismatch");
        Require(nearMiss.Result.Status == ReadStatus::Implausible,
                "unapproved-property near-miss did not stay rejected");
        Require(nearMiss.Result.Reason.find("lifecycle_function_FName_near_miss_rejected") !=
                    std::string::npos,
                "unapproved-property near-miss reason missing rejected marker");
        Require(nearMiss.Result.Reason.find("cause_property_FName_chain_unapproved") !=
                    std::string::npos,
                "unapproved-property near-miss reason missing property-chain cause");
        Require(nearMiss.Result.Reason.find("expected_property_name_indices_28411.21307.22961.28509.17716") !=
                    std::string::npos,
                "unapproved-property near-miss reason missing expected property chain");
        Require(nearMiss.Result.Reason.find("observed_property_name_indices_28419.21315.22969.28517.17725") !=
                    std::string::npos,
                "unapproved-property near-miss reason missing observed property chain");
        RequireNearMissReasonMetadataClassification(
            nearMiss.Result.Reason,
            "unapproved-property near-miss reason lost metadata-only classification");
        RequireNearMissReasonCarriesEarlyPropertyChains(
            nearMiss.Result.Reason,
            "28411.21307.22961.28509.17716",
            "28419.21315.22969.28517.17725",
            "unapproved-property near-miss reason did not preserve early property chains");

        BuildObservedHandleNewPlayerFunction(fixture);
        WriteObject(fixture.Outer,
                    kShooterGameModeNameIndex + 1,
                    kShooterGameModeObjectIndex + 1,
                    nullptr,
                    nullptr);
        WriteObject(fixture.Function,
                    kHandleNewPlayerNameIndex + 700,
                    kHandleNewPlayerNameIndex,
                    fixture.FunctionClass.data(),
                    fixture.Outer.data());
        Require(Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                     kHandleNewPlayerNameIndex + 700,
                                                                     fixture.Reader(),
                                                                     fixture.Function.data(),
                                                                     nearMiss),
                "outer-mismatch HandleNewPlayer-shaped near miss was not diagnosed");
        Require(nearMiss.Function == LifecycleFunction::HandleNewPlayer,
                "outer-mismatch near-miss function kind mismatch");
        Require(nearMiss.Result.Status == ReadStatus::Implausible,
                "outer-mismatch near-miss did not stay rejected");
        Require(nearMiss.Result.Reason.find("cause_outer_mismatch") != std::string::npos,
                "outer-mismatch near-miss reason missing outer cause");
        Require(nearMiss.Result.Reason.find("expected_outer_name_index_9755") !=
                    std::string::npos,
                "outer-mismatch near-miss reason missing expected outer FName");
        Require(nearMiss.Result.Reason.find("observed_outer_name_index_9756") !=
                    std::string::npos,
                "outer-mismatch near-miss reason missing observed outer FName");
        RequireNearMissReasonMetadataClassification(
            nearMiss.Result.Reason,
            "outer-mismatch near-miss reason lost metadata-only classification");
        RequireNearMissReasonCarriesEarlyPropertyChains(
            nearMiss.Result.Reason,
            "28411.21307.22961.28509.17716",
            "28418.21314.22968.28516.17724",
            "outer-mismatch near-miss reason did not preserve early property chains");

        std::atomic<uint64_t> scanCounter{0};
        uint64_t scanNumber = 99;
        Require(Observer::TryReserveObservationBudget(scanCounter, 1, scanNumber),
                "near-miss scan budget was not reserved");
        Require(scanNumber == 1, "near-miss scan sequence mismatch");
        Require(!Observer::TryReserveObservationBudget(scanCounter, 1, scanNumber),
                "near-miss scan budget allowed a second reservation");
        Require(scanNumber == 0, "near-miss exhausted scan budget left a sequence");

        std::atomic<uint64_t> diagnosticCounter{0};
        uint64_t diagnosticNumber = 99;
        Require(Observer::TryReserveObservationBudget(diagnosticCounter, 1, diagnosticNumber),
                "near-miss diagnostic candidate budget was not reserved");
        Require(diagnosticNumber == 1, "near-miss diagnostic sequence mismatch");
        Require(!Observer::TryReserveObservationBudget(diagnosticCounter, 1, diagnosticNumber),
                "near-miss diagnostic candidate budget allowed a second reservation");
        Require(diagnosticNumber == 0, "near-miss exhausted diagnostic budget left a sequence");

        Observer::Attempt attempt = Observer::TryIdentifyInvocation(EnabledGate(),
                                                                    kHandleNewPlayerNameIndex + 500,
                                                                    fixture.Reader(),
                                                                    fixture.Function.data(),
                                                                    fixture.Params.data());
        Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "near-miss function reached accepted lifecycle identify path");

        std::atomic<uint64_t> acceptedCounter{0};
        uint64_t observationNumber = 99;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kHandleNewPlayerNameIndex + 500,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "near-miss function reached accepted lifecycle observer path");
        Require(observationNumber == 0, "near-miss reserved an accepted observer sequence");
        Require(acceptedCounter.load(std::memory_order_relaxed) == 0,
                "near-miss consumed accepted observer budget");
        Require(scanCounter.load(std::memory_order_relaxed) == 1,
                "accepted near-miss path changed scan budget unexpectedly");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == 1,
                "accepted near-miss path changed diagnostic candidate budget unexpectedly");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "near-miss built copied lifecycle evidence");
        Require(observation.BoolCount == 0, "near-miss left copied bool payload");
        Require(observation.RedactedCount == 0, "near-miss left redacted field payload");
        RequireNoPlayerPrincipalEventView(observation, "near-miss built internal event-view evidence");

        WriteAt(fixture.Function, 0x90, kCheckJoinInProgressFunctionFlags);
        Require(!Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                      kHandleNewPlayerNameIndex + 500,
                                                                      fixture.Reader(),
                                                                      fixture.Function.data(),
                                                                      nearMiss),
                "malformed near-miss function was diagnosed");

        BuildObservedHandleNewPlayerFunction(fixture);
        Require(!Observer::TryIdentifyFunctionFNameNearMissDiagnostic(EnabledGate(),
                                                                      kHandleNewPlayerNameIndex,
                                                                      fixture.Reader(),
                                                                      fixture.Function.data(),
                                                                      nearMiss),
                "exact lifecycle function was reported as a near-miss diagnostic");

        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        observationNumber = 99;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "near-miss diagnostic budgets hid a valid accepted lifecycle observation");
        Require(observationNumber == 1,
                "valid accepted lifecycle observation did not keep an independent sequence");
        Require(acceptedCounter.load(std::memory_order_relaxed) == 1,
                "valid accepted lifecycle observation did not reserve exactly one accepted budget slot");
        Require(scanCounter.load(std::memory_order_relaxed) == 1,
                "valid accepted lifecycle observation changed near-miss scan budget");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == 1,
                "valid accepted lifecycle observation changed diagnostic candidate budget");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                               Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                               2,
                               "valid accepted lifecycle observation did not build event-view evidence");
        ResetProcessLocalSubjectTokensForTesting();
    }

    void TestDispatchGateOnlyCannotBuildLifecycleEvent()
    {
        Observer::Gate gate = Observer::EvaluateGate("1", true, true, true, kSupportedSha, "10", "1");
        Require(gate.Status == Observer::GateStatus::NonZeroDispatchLimit,
                "non-zero dispatch limit did not fail the observer gate");
        Require(!gate.Enabled(), "non-zero dispatch limit enabled the observer gate");

        MemoryReader reader{ThrowingReader, nullptr};
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(
            gate,
            kHandleNewPlayerNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            nullptr,
            counter,
            observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Disabled,
                "non-zero dispatch gate attempted lifecycle observation");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "non-zero dispatch gate reserved observation budget");
        Require(observationNumber == 0, "non-zero dispatch gate left an observation sequence");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "non-zero dispatch gate left reflected lifecycle material");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "non-zero dispatch gate built accepted lifecycle observation");
        Require(observation.BoolCount == 0, "non-zero dispatch gate left copied bools");
        Require(observation.RedactedCount == 0, "non-zero dispatch gate left redacted fields");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(!Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event),
                "non-zero dispatch gate built internal event view");
    }

    void TestBuildsHandleNewPlayerObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "valid HandleNewPlayer observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStart, "session start role mismatch");
        Require(observation.Action == Observer::PrincipalAction::CandidateCreated,
                "candidate-created action mismatch");
        Require(observation.BoolCount == 2, "HandleNewPlayer bool count mismatch");
        Require(observation.RedactedCount == 3, "HandleNewPlayer redacted count mismatch");
        Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin, "first bool field mismatch");
        Require(observation.BoolStorage[0].Value, "bIsFromLogin bool value mismatch");
        Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue, "second bool field mismatch");
        Require(observation.BoolStorage[1].Value, "ReturnValue bool value mismatch");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "login-backed HandleNewPlayer 1,0 built rejected-start lifecycle evidence");
        Require(observation.BoolCount == 0, "login-backed HandleNewPlayer 1,0 rejection left bools");
        Require(observation.RedactedCount == 0, "login-backed HandleNewPlayer 1,0 rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "login-backed HandleNewPlayer 1,0 built internal event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(0, 1), observation),
                "non-login HandleNewPlayer 0,1 built lifecycle evidence");
        Require(observation.BoolCount == 0, "non-login HandleNewPlayer 0,1 rejection left bools");
        Require(observation.RedactedCount == 0, "non-login HandleNewPlayer 0,1 rejection left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "non-login HandleNewPlayer 0,1 built internal event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(0, 0), observation),
                "non-login HandleNewPlayer 0,0 built lifecycle evidence");
        Require(observation.BoolCount == 0, "non-login HandleNewPlayer 0,0 rejection left bools");
        Require(observation.RedactedCount == 0, "non-login HandleNewPlayer 0,0 rejection left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "non-login HandleNewPlayer 0,0 built internal event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(2, 1), observation),
                "non-canonical lifecycle bool accepted");
        Require(observation.BoolCount == 0, "failed lifecycle copy left bools");

        Require(Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 0), observation),
                "rejected CheckJoinInProgress observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "CheckJoinInProgress session_start_rejected role mismatch");
        Require(observation.Action == Observer::PrincipalAction::None,
                "CheckJoinInProgress session_start_rejected action mismatch");
        Require(observation.BoolCount == 2, "CheckJoinInProgress bool count mismatch");
        Require(observation.RedactedCount == 1, "CheckJoinInProgress redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::NewPlayer,
                "CheckJoinInProgress redacted field mismatch");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "CheckJoinInProgress copied a private subject token");
        LifecycleInvocation tokenedCheckJoin = CheckJoinInProgressInvocation(1, 0);
        tokenedCheckJoin.Fields[1].ProcessLocalSubjectToken = 42;
        Require(Observer::TryBuildCopiedLifecycleObservation(tokenedCheckJoin, observation),
                "tokened CheckJoinInProgress rejected observation rejected");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "tokened CheckJoinInProgress retained private subject token");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "CheckJoinInProgress session_start_rejected event view rejected");

        Require(!Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 1), observation),
                "accepted CheckJoinInProgress result built lifecycle evidence");
        Require(observation.BoolCount == 0, "accepted CheckJoinInProgress rejection left bools");
        Require(!Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(0, 0), observation),
                "non-login CheckJoinInProgress result built lifecycle evidence");
        Require(observation.BoolCount == 0, "non-login CheckJoinInProgress rejection left bools");
    }

    void TestAcceptedObserverTripletsStaySeparateFromDiagnosticCandidates()
    {
        {
            const LifecycleInvocation invocation = HandleNewPlayerInvocation(1, 1);
            Observer::CopiedLifecycleObservation observation;
            Require(Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                    "accepted session_start observation rejected");
            RequirePlayerPrincipalEventView(observation,
                                            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                                            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                                            2,
                                            "accepted session_start event view rejected");
            RequireNoDiagnosticObservationForAcceptedInvocation(
                invocation,
                "accepted session_start was also copied as a diagnostic candidate");
        }

        {
            const LifecycleInvocation invocation = HandleNewPlayerInvocation(1, 0);
            Observer::CopiedLifecycleObservation observation;
            Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                    "login-backed HandleNewPlayer 1,0 built accepted observer event");
            RequireNoAcceptedObservationForDiagnosticInvocation(
                invocation,
                "login-backed HandleNewPlayer 1,0 built diagnostic observer event");
            RequireNoPlayerPrincipalEventView(
                observation,
                "login-backed HandleNewPlayer 1,0 built internal event-view evidence");
        }

        {
            const LifecycleInvocation invocation = CheckJoinInProgressInvocation(1, 0);
            Observer::CopiedLifecycleObservation observation;
            Require(Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                    "accepted CheckJoinInProgress session_start_rejected observation rejected");
            RequirePlayerPrincipalEventView(observation,
                                            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                                            Obelisk::Core::PlayerPrincipalAction::None,
                                            2,
                                            "accepted CheckJoinInProgress session_start_rejected event view rejected");
            RequireNoDiagnosticObservationForAcceptedInvocation(
                invocation,
                "accepted CheckJoinInProgress session_start_rejected was also copied as a diagnostic candidate");
        }

        {
            const LifecycleInvocation invocation = OnLogoutInvocation();
            Observer::CopiedLifecycleObservation observation;
            Require(Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                    "accepted session_end observation rejected");
            RequirePlayerPrincipalEventView(observation,
                                            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                                            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                                            0,
                                            "accepted session_end event view rejected");
            RequireNoDiagnosticObservationForAcceptedInvocation(
                invocation,
                "accepted session_end was also copied as a diagnostic candidate");
        }

        {
            const LifecycleInvocation invocation = CheckJoinInProgressInvocation(1, 1);
            Observer::CopiedLifecycleObservation diagnosticObservation;
            Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(invocation,
                                                                          diagnosticObservation),
                    "CheckJoinInProgress diagnostic copy rejected");
            RequireNoAcceptedObservationForDiagnosticInvocation(
                invocation,
                "CheckJoinInProgress diagnostic built an accepted observer event");
            RequireNoPlayerPrincipalEventView(
                diagnosticObservation,
                "CheckJoinInProgress diagnostic built internal event-view evidence");
        }

        {
            const LifecycleInvocation invocation = K2PostLoginInvocation();
            Observer::CopiedLifecycleObservation diagnosticObservation;
            Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(invocation,
                                                                          diagnosticObservation),
                    "K2_PostLogin diagnostic copy rejected");
            RequireNoAcceptedObservationForDiagnosticInvocation(
                invocation,
                "K2_PostLogin diagnostic built an accepted observer event");
            RequireNoPlayerPrincipalEventView(
                diagnosticObservation,
                "K2_PostLogin diagnostic built internal event-view evidence");
        }
    }

    void TestBuildsCheckJoinInProgressDiagnosticOnlyObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 1), observation),
                "CheckJoinInProgress built accepted lifecycle observation");
        Require(observation.BoolCount == 0, "failed accepted lifecycle copy left diagnostic bools");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CheckJoinInProgressInvocation(1, 1),
                    observation),
                "valid CheckJoinInProgress diagnostic observation rejected");
        Require(observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic,
                "CheckJoinInProgress diagnostic function mismatch");
        Require(observation.Role == Observer::LifecycleRole::DiagnosticOnly,
                "CheckJoinInProgress diagnostic role mismatch");
        Require(std::strcmp(Observer::LifecycleRoleName(observation.Role),
                            "diagnostic_only") == 0,
                "CheckJoinInProgress diagnostic role token mismatch");
        Require(observation.FunctionNameIndex == kCheckJoinInProgressNameIndex,
                "CheckJoinInProgress diagnostic FName mismatch");
        Require(observation.OuterNameIndex == kShooterGameModeNameIndex,
                "CheckJoinInProgress diagnostic outer mismatch");
        Require(observation.BoolCount == 2, "CheckJoinInProgress diagnostic bool count mismatch");
        Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin,
                "CheckJoinInProgress first bool mismatch");
        Require(observation.BoolStorage[0].Value, "CheckJoinInProgress bIsFromLogin value mismatch");
        Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue,
                "CheckJoinInProgress second bool mismatch");
        Require(observation.BoolStorage[1].Value, "CheckJoinInProgress ReturnValue value mismatch");
        Require(observation.RedactedCount == 1, "CheckJoinInProgress redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::NewPlayer,
                "CheckJoinInProgress redacted field mismatch");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(!Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event),
                "CheckJoinInProgress diagnostic built internal event view");

        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CheckJoinInProgressInvocation(2, 0),
                    observation),
                "non-canonical CheckJoinInProgress diagnostic bool accepted");
        Require(observation.BoolCount == 0, "failed CheckJoinInProgress diagnostic copy left bools");

        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CheckJoinInProgressInvocation(1, 2),
                    observation),
                "non-canonical CheckJoinInProgress diagnostic ReturnValue accepted");
        Require(observation.BoolCount == 0,
                "failed CheckJoinInProgress ReturnValue diagnostic copy left bools");

        for (const auto [isFromLogin, returnValue] : {
                 std::pair<uint8_t, uint8_t>{1, 1},
                 std::pair<uint8_t, uint8_t>{0, 1},
                 std::pair<uint8_t, uint8_t>{0, 0},
             })
        {
            const LifecycleInvocation tupleInvocation =
                CheckJoinInProgressInvocation(isFromLogin, returnValue);
            Require(!Observer::TryBuildCopiedLifecycleObservation(tupleInvocation,
                                                                  observation),
                    "non-rejected CheckJoinInProgress tuple built accepted lifecycle evidence");
            Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(tupleInvocation,
                                                                          observation),
                    "non-rejected CheckJoinInProgress tuple rejected diagnostic copy");
            Require(observation.BoolCount == 2,
                    "CheckJoinInProgress diagnostic tuple bool count mismatch");
            Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin,
                    "CheckJoinInProgress diagnostic tuple first bool field mismatch");
            Require(observation.BoolStorage[0].Value == (isFromLogin != 0),
                    "CheckJoinInProgress diagnostic tuple bIsFromLogin mismatch");
            Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue,
                    "CheckJoinInProgress diagnostic tuple second bool field mismatch");
            Require(observation.BoolStorage[1].Value == (returnValue != 0),
                    "CheckJoinInProgress diagnostic tuple ReturnValue mismatch");
            RequireNoPlayerPrincipalEventView(
                observation,
                "CheckJoinInProgress diagnostic tuple built internal event-view evidence");
        }

        LifecycleInvocation tokenedDiagnostic = CheckJoinInProgressInvocation(1, 1);
        tokenedDiagnostic.Fields[1].ProcessLocalSubjectToken = 42;
        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(tokenedDiagnostic,
                                                                      observation),
                "tokened CheckJoinInProgress diagnostic observation rejected");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "CheckJoinInProgress diagnostic retained a private subject token");
        RequireNoPlayerPrincipalEventView(
            observation,
            "tokened CheckJoinInProgress diagnostic built internal event-view evidence");
    }

    void TestBuildsK2PostLoginDiagnosticOnlyObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(K2PostLoginInvocation(), observation),
                "K2_PostLogin built accepted lifecycle observation");
        Require(observation.BoolCount == 0, "failed accepted lifecycle copy left K2 bools");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(K2PostLoginInvocation(), observation),
                "valid K2_PostLogin diagnostic observation rejected");
        Require(observation.Function == LifecycleFunction::K2PostLoginDiagnostic,
                "K2_PostLogin diagnostic function mismatch");
        Require(observation.Role == Observer::LifecycleRole::DiagnosticOnly,
                "K2_PostLogin diagnostic role mismatch");
        Require(std::strcmp(Observer::LifecycleRoleName(observation.Role),
                            "diagnostic_only") == 0,
                "K2_PostLogin diagnostic role token mismatch");
        Require(observation.FunctionNameIndex == kGameModeK2PostLoginNameIndex,
                "K2_PostLogin diagnostic FName mismatch");
        Require(observation.OuterNameIndex == kGameModeNameIndex,
                "K2_PostLogin diagnostic outer mismatch");
        Require(observation.BoolCount == 0, "K2_PostLogin diagnostic copied bools");
        Require(observation.RedactedCount == 1, "K2_PostLogin redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::NewPlayer,
                "K2_PostLogin redacted field mismatch");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(!Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event),
                "K2_PostLogin diagnostic built internal event view");

        LifecycleInvocation forgedK2 = K2PostLoginInvocation();
        static uint8_t forgedBool = 1;
        forgedK2.Fields.push_back(BoolField(LifecycleField::BIsFromLogin,
                                            kBIsFromLoginNameIndex,
                                            0x08,
                                            &forgedBool));
        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(forgedK2, observation),
                "K2_PostLogin diagnostic accepted copied bool payload");
        Require(observation.BoolCount == 0, "failed K2_PostLogin diagnostic copy left bools");
    }

    void TestDiagnosticOnlyMatchedAttemptsNeverBuildLifecycleEventAfterOriginal()
    {
        Observer::CopiedLifecycleObservation observation;
        Observer::Attempt attempt;
        attempt.Status = Observer::AttemptStatus::Matched;
        attempt.Result = ReadResult::Ok();
        attempt.Invocation = CheckJoinInProgressInvocation(1, 1);

        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "CheckJoinInProgress matched diagnostic built post-original lifecycle event");
        Require(observation.BoolCount == 0, "CheckJoinInProgress post-original rejection left bools");
        Require(observation.RedactedCount == 0, "CheckJoinInProgress post-original rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "CheckJoinInProgress diagnostic post-original rejection built internal event view");

        attempt.Invocation = K2PostLoginInvocation();
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "K2_PostLogin matched diagnostic built post-original lifecycle event");
        Require(observation.BoolCount == 0, "K2_PostLogin post-original rejection left bools");
        Require(observation.RedactedCount == 0, "K2_PostLogin post-original rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "K2_PostLogin diagnostic post-original rejection built internal event view");
    }

    void TestOrganicJoinDiagnosticCandidatesRemainNonDispatchable()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "organic join diagnostic test gate was not enabled");

        MemoryReader reader{ThrowingReader, nullptr};
        for (int32_t nameIndex : {
                 kGameModeK2PostLoginNameIndex,
                 kOnPostLoginDelegateNameIndex,
                 kOnStartNewPlayerDelegateNameIndex,
             })
        {
            Require(Observer::IsLifecycleDiagnosticCandidateNameIndex(nameIndex),
                    "organic join candidate was not diagnostic-visible");
            Require(!Observer::IsReflectedLifecycleNameIndex(nameIndex),
                    "organic join diagnostic candidate was promoted to accepted lifecycle target");

            std::atomic<uint64_t> counter{0};
            uint64_t observationNumber = 99;
            Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                       nameIndex,
                                                                       reader,
                                                                       reinterpret_cast<void*>(0x10000),
                                                                       nullptr,
                                                                       counter,
                                                                       observationNumber);
            Require(attempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                    "organic join diagnostic candidate reached accepted observer path");
            Require(counter.load(std::memory_order_relaxed) == 0,
                    "organic join diagnostic candidate reserved accepted event budget");
            Require(observationNumber == 0,
                    "organic join diagnostic candidate left an accepted event sequence");
            Require(attempt.Invocation.FunctionNameIndex == -1,
                    "organic join diagnostic candidate retained reflected invocation material");

            Observer::CopiedLifecycleObservation observation;
            Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                               attempt,
                                                                               observation),
                    "organic join diagnostic candidate built copied lifecycle evidence");
            Require(observation.BoolCount == 0,
                    "organic join diagnostic candidate left copied bools");
            Require(observation.RedactedCount == 0,
                    "organic join diagnostic candidate left redactions");
            RequireNoPlayerPrincipalEventView(
                observation,
                "organic join diagnostic candidate built internal event-view evidence");
        }
    }

    void TestCheckJoinInProgressRejectedPathIsReachableThroughObserver()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "CheckJoinInProgress observer test gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildCheckJoinInProgressFunction(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "rejected CheckJoinInProgress did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 1, "rejected CheckJoinInProgress sequence mismatch");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "rejected CheckJoinInProgress did not reserve one observation");
        Require(attempt.Invocation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic,
                "rejected CheckJoinInProgress function mismatch");
        Require(attempt.Invocation.FunctionNameIndex == kCheckJoinInProgressNameIndex,
                "rejected CheckJoinInProgress FName mismatch");
        Require(attempt.Invocation.OuterNameIndex == kShooterGameModeNameIndex,
                "rejected CheckJoinInProgress outer mismatch");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(false, attempt, observation),
                "pre-original CheckJoinInProgress built copied event");
        Require(observation.BoolCount == 0, "pre-original CheckJoinInProgress left copied bools");
        Require(observation.RedactedCount == 0, "pre-original CheckJoinInProgress left redactions");

        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original CheckJoinInProgress did not build copied event");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "CheckJoinInProgress observer role mismatch");
        Require(observation.Action == Observer::PrincipalAction::None,
                "CheckJoinInProgress observer action mismatch");
        Require(observation.BoolCount == 2, "CheckJoinInProgress observer bool count mismatch");
        Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin,
                "CheckJoinInProgress observer first bool field mismatch");
        Require(observation.BoolStorage[0].Value,
                "CheckJoinInProgress observer bIsFromLogin mismatch");
        Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue,
                "CheckJoinInProgress observer second bool field mismatch");
        Require(!observation.BoolStorage[1].Value,
                "CheckJoinInProgress observer ReturnValue mismatch");
        Require(observation.RedactedCount == 1, "CheckJoinInProgress observer redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::NewPlayer,
                "CheckJoinInProgress observer redacted field mismatch");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "CheckJoinInProgress observer copied a private subject token");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            attempt.Invocation,
            "accepted CheckJoinInProgress observer event copied as diagnostic evidence");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "CheckJoinInProgress observer event-view data rejected");

        BuildCheckJoinInProgressFunction(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 1;
        observationNumber = 99;
        Observer::Attempt acceptedCheckAttempt = Observer::TryObserveInvocation(gate,
                                                                               kCheckJoinInProgressNameIndex,
                                                                               fixture.Reader(),
                                                                               fixture.Function.data(),
                                                                               fixture.Params.data(),
                                                                               counter,
                                                                               observationNumber);
        Require(acceptedCheckAttempt.Status == Observer::AttemptStatus::Rejected,
                "accepted CheckJoinInProgress result built lifecycle event evidence");
        Require(observationNumber == 0,
                "accepted CheckJoinInProgress result reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "accepted CheckJoinInProgress result consumed observer budget");
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(
                    true,
                    acceptedCheckAttempt,
                    observation),
                "accepted CheckJoinInProgress result built copied lifecycle evidence");
        RequireNoPlayerPrincipalEventView(
            observation,
                "accepted CheckJoinInProgress result built internal event-view evidence");
    }

    void TestHandleNewPlayerOneZeroRejectedThroughObserverWithoutBudget()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "HandleNewPlayer observer test gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "HandleNewPlayer 1,0 matched accepted observer path");
        Require(observationNumber == 0,
                "HandleNewPlayer 1,0 reserved an accepted event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "HandleNewPlayer 1,0 consumed accepted observer budget");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "HandleNewPlayer 1,0 built post-original lifecycle evidence");
        Require(observation.BoolCount == 0,
                "HandleNewPlayer 1,0 post-original rejection left copied bools");
        Require(observation.RedactedCount == 0,
                "HandleNewPlayer 1,0 post-original rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "HandleNewPlayer 1,0 built internal event-view evidence");
    }

    void TestCheckJoinInProgressRejectedPathIgnoresRedactedObjectPointer()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "CheckJoinInProgress redacted object test gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildCheckJoinInProgressFunction(fixture);
        fixture.Params[0x00] = 1;
        WriteAt(fixture.Params, 0x08, std::numeric_limits<uintptr_t>::max());
        fixture.Params[0x10] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);

        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "CheckJoinInProgress rejected path validated a redacted object pointer");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 1,
                "CheckJoinInProgress redacted object path did not reserve an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "CheckJoinInProgress redacted object path did not consume one event budget slot");
        Require(attempt.Invocation.Fields.size() == 3,
                "CheckJoinInProgress redacted object invocation field count mismatch");
        Require(attempt.Invocation.Fields[1].Field == LifecycleField::NewPlayer,
                "CheckJoinInProgress redacted object field mismatch");
        Require(attempt.Invocation.Fields[1].Range.Data == nullptr,
                "CheckJoinInProgress redacted object field exposed a range");
        Require(attempt.Invocation.Fields[1].ProcessLocalSubjectToken == 0,
                "CheckJoinInProgress redacted object field retained a subject token");

        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "CheckJoinInProgress redacted object path did not build copied event");
        Require(observation.Role == Observer::LifecycleRole::SessionStartRejected,
                "CheckJoinInProgress redacted object role mismatch");
        Require(observation.BoolCount == 2,
                "CheckJoinInProgress redacted object copied bool count mismatch");
        Require(observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin &&
                    observation.BoolStorage[0].Value,
                "CheckJoinInProgress redacted object bIsFromLogin mismatch");
        Require(observation.BoolStorage[1].Field == LifecycleField::ReturnValue &&
                    !observation.BoolStorage[1].Value,
                "CheckJoinInProgress redacted object ReturnValue mismatch");
        Require(observation.RedactedCount == 1 &&
                    observation.RedactedStorage[0] == LifecycleField::NewPlayer,
                "CheckJoinInProgress redacted object redaction mismatch");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "CheckJoinInProgress redacted object copied a private subject token");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "CheckJoinInProgress redacted object event-view data rejected");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            attempt.Invocation,
            "CheckJoinInProgress redacted object event copied as diagnostic evidence");
    }

    void TestRejectsInferredCheckJoinInProgressDrift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(
                    InferredRagnarokCheckJoinInProgressRestart20260606DriftInvocation(1, 0),
                    observation),
                "inferred CheckJoinInProgress drift built copied event");
        Require(observation.BoolCount == 0,
                "inferred CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "inferred CheckJoinInProgress drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "inferred CheckJoinInProgress drift built internal event-view evidence");

        LifecycleReflectionFixture fixture;
        BuildInferredCheckJoinInProgressRestart20260606Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "inferred CheckJoinInProgress drift matched through observer path");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "inferred CheckJoinInProgress drift did not fail implausibly");
        Require(attempt.Result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "inferred CheckJoinInProgress drift reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "inferred CheckJoinInProgress drift consumed observer budget");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "inferred CheckJoinInProgress drift retained reflected invocation material");

        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "post-original inferred CheckJoinInProgress drift built copied event");
        Require(observation.BoolCount == 0,
                "post-original inferred CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "post-original inferred CheckJoinInProgress drift left redactions");
    }

    void TestAcceptsObservedCheckJoinInProgressDrift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokCheckJoinInProgressRestart20260607DriftInvocation(1, 0),
                    observation),
                "observed CheckJoinInProgress drift rejected copied event");
        Require(observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic,
                "observed CheckJoinInProgress drift function mismatch");
        Require(observation.BoolCount == 2,
                "observed CheckJoinInProgress drift bool count mismatch");
        Require(observation.BoolStorage[0].Value,
                "observed CheckJoinInProgress drift bIsFromLogin mismatch");
        Require(!observation.BoolStorage[1].Value,
                "observed CheckJoinInProgress drift ReturnValue mismatch");
        Require(observation.RedactedCount == 1,
                "observed CheckJoinInProgress drift redacted count mismatch");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "observed CheckJoinInProgress drift copied a private subject token");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "observed CheckJoinInProgress drift did not build internal event view");

        LifecycleReflectionFixture fixture;
        BuildObservedCheckJoinInProgressRestart20260607Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "observed CheckJoinInProgress drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 1,
                "observed CheckJoinInProgress drift sequence mismatch");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "observed CheckJoinInProgress drift budget mismatch");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 3,
                "observed CheckJoinInProgress drift count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          attempt,
                                                                          observation),
                "post-original observed CheckJoinInProgress drift did not build copied event");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "post-original observed CheckJoinInProgress drift did not build internal event view");

        Require(!Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokCheckJoinInProgressRestart20260607DriftInvocation(1, 1),
                    observation),
                "accepted CheckJoinInProgress drift result built lifecycle evidence");
        Require(observation.BoolCount == 0,
                "accepted CheckJoinInProgress drift rejection left copied bools");
    }

    void TestAcceptsLiveObservedCheckJoinInProgressDrift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokCheckJoinInProgressLive20260607DriftInvocation(1, 0),
                    observation),
                "live observed CheckJoinInProgress drift rejected copied event");
        Require(observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic,
                "live observed CheckJoinInProgress drift function mismatch");
        Require(observation.BoolCount == 2,
                "live observed CheckJoinInProgress drift bool count mismatch");
        Require(observation.RedactedCount == 1,
                "live observed CheckJoinInProgress drift redacted count mismatch");

        LifecycleReflectionFixture fixture;
        BuildObservedCheckJoinInProgressLive20260607Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "live observed CheckJoinInProgress drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 3,
                "live observed CheckJoinInProgress drift count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          attempt,
                                                                          observation),
                "post-original live observed CheckJoinInProgress drift did not build copied event");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "post-original live observed CheckJoinInProgress drift did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedTheIslandCheckJoinInProgress20260607DriftInvocation(1, 0),
                    observation),
                "TheIsland CheckJoinInProgress drift rejected copied event");
        Require(observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic,
                "TheIsland CheckJoinInProgress drift function mismatch");
        Require(observation.BoolCount == 2,
                "TheIsland CheckJoinInProgress drift bool count mismatch");
        Require(observation.RedactedCount == 1,
                "TheIsland CheckJoinInProgress drift redacted count mismatch");

        BuildObservedCheckJoinInProgressTheIsland20260607Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;
        counter.store(0, std::memory_order_relaxed);
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kCheckJoinInProgressNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "TheIsland CheckJoinInProgress drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 3,
                "TheIsland CheckJoinInProgress drift count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          attempt,
                                                                          observation),
                "post-original TheIsland CheckJoinInProgress drift did not build copied event");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "post-original TheIsland CheckJoinInProgress drift did not build internal event view");
    }

    void TestRejectsMixedCurrentRuntimeCheckJoinInProgressDrift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(
                    MixedCurrentRuntimeCheckJoinInProgressTheIslandRagnarokLive20260607DriftInvocation(1, 0),
                    observation),
                "mixed current-runtime CheckJoinInProgress drift built copied event");
        Require(observation.BoolCount == 0,
                "mixed current-runtime CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "mixed current-runtime CheckJoinInProgress drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "mixed current-runtime CheckJoinInProgress drift built internal event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    MixedCurrentRuntimeCheckJoinInProgressTheIslandRagnarokLive20260607DriftInvocation(1, 1),
                    observation),
                "mixed current-runtime CheckJoinInProgress drift built diagnostic observation");
        Require(observation.BoolCount == 0,
                "mixed current-runtime CheckJoinInProgress diagnostic drift left copied bools");
        Require(observation.RedactedCount == 0,
                "mixed current-runtime CheckJoinInProgress diagnostic drift left redactions");

        LifecycleReflectionFixture fixture;
        BuildMixedCurrentRuntimeCheckJoinInProgressTheIslandRagnarokLive20260607Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        Observer::Gate gate = EnabledGate();
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "mixed current-runtime CheckJoinInProgress drift matched through observer path");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "mixed current-runtime CheckJoinInProgress drift did not fail implausibly");
        RequireCurrentRuntimeOfflineSourceDiagnostic(
            attempt.Result.Reason,
            "ShooterGameMode.CheckJoinInProgress",
            "28509.28411.17716",
            "28520.28422.17720");
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "mixed current-runtime CheckJoinInProgress drift reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "mixed current-runtime CheckJoinInProgress drift consumed observer budget");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "mixed current-runtime CheckJoinInProgress drift retained reflected invocation material");

        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "post-original mixed current-runtime CheckJoinInProgress drift built copied event");
        Require(observation.BoolCount == 0,
                "post-original mixed current-runtime CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "post-original mixed current-runtime CheckJoinInProgress drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "post-original mixed current-runtime CheckJoinInProgress drift built internal event view");
    }

    void TestRejectsCurrentRagnarokCheckJoinInProgressName28514Drift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(
                    UnapprovedRagnarokCheckJoinInProgressLive20260607T150504DriftInvocation(1, 0),
                    observation),
                "current Ragnarok CheckJoinInProgress 28514/28416/17723 drift built copied event");
        Require(observation.BoolCount == 0,
                "current Ragnarok CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "current Ragnarok CheckJoinInProgress drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "current Ragnarok CheckJoinInProgress drift built internal event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    UnapprovedRagnarokCheckJoinInProgressLive20260607T150504DriftInvocation(1, 1),
                    observation),
                "current Ragnarok CheckJoinInProgress drift built diagnostic observation");
        Require(observation.BoolCount == 0,
                "current Ragnarok CheckJoinInProgress diagnostic drift left copied bools");
        Require(observation.RedactedCount == 0,
                "current Ragnarok CheckJoinInProgress diagnostic drift left redactions");

        LifecycleReflectionFixture fixture;
        BuildUnapprovedCheckJoinInProgressLive20260607T150504Function(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;

        Observer::Gate gate = EnabledGate();
        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kCheckJoinInProgressNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "current Ragnarok CheckJoinInProgress drift matched through observer path");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "current Ragnarok CheckJoinInProgress drift did not fail implausibly");
        Require(attempt.Result.Reason.find(
                    "lifecycle_property_FName_mismatch_expected_name_index_28509") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("cause_unapproved_observed_property_FName") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("observed_property_fname_chain=28514.28416.17723") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "current Ragnarok CheckJoinInProgress drift reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "current Ragnarok CheckJoinInProgress drift consumed observer budget");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "current Ragnarok CheckJoinInProgress drift retained reflected invocation material");

        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "post-original current Ragnarok CheckJoinInProgress drift built copied event");
        Require(observation.BoolCount == 0,
                "post-original current Ragnarok CheckJoinInProgress drift left copied bools");
        Require(observation.RedactedCount == 0,
                "post-original current Ragnarok CheckJoinInProgress drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "post-original current Ragnarok CheckJoinInProgress drift built internal event view");

        Observer::Attempt diagnosticAttempt =
            Observer::TryIdentifyDiagnosticCandidateInvocation(gate,
                                                               kCheckJoinInProgressNameIndex,
                                                               fixture.Reader(),
                                                               fixture.Function.data(),
                                                               fixture.Params.data());
        Require(diagnosticAttempt.Status == Observer::AttemptStatus::Rejected,
                "current Ragnarok CheckJoinInProgress drift matched diagnostic candidate path");
        Require(diagnosticAttempt.Result.Status == ReadStatus::Implausible,
                "current Ragnarok CheckJoinInProgress diagnostic drift did not fail implausibly");
        Require(diagnosticAttempt.Invocation.FunctionNameIndex == -1,
                "current Ragnarok CheckJoinInProgress diagnostic drift retained invocation material");
    }

    void TestCheckJoinInProgressRejectedLogFieldsStayAnalyzerSafe()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 0),
                                                             observation),
                "CheckJoinInProgress rejected fixture did not build copied event");
        Require(std::strcmp(Observer::LifecycleRoleName(observation.Role),
                            "session_start_rejected") == 0,
                "CheckJoinInProgress rejected role log token mismatch");
        Require(std::strcmp(Observer::LifecycleTargetName(observation.Function),
                            "ShooterGameMode.CheckJoinInProgress") == 0,
                "CheckJoinInProgress rejected target log token mismatch");
        Require(std::strcmp(Observer::PrincipalActionName(observation.Action), "none") == 0,
                "CheckJoinInProgress rejected principal action log token mismatch");
        Require(observation.BoolCount == 2, "CheckJoinInProgress rejected bool count mismatch");
        Require(std::strcmp(Observer::LifecycleFieldName(observation.BoolStorage[0].Field),
                            "bIsFromLogin") == 0,
                "CheckJoinInProgress rejected first bool log token mismatch");
        Require(observation.BoolStorage[0].Value,
                "CheckJoinInProgress rejected bIsFromLogin value mismatch");
        Require(std::strcmp(Observer::LifecycleFieldName(observation.BoolStorage[1].Field),
                            "ReturnValue") == 0,
                "CheckJoinInProgress rejected second bool log token mismatch");
        Require(!observation.BoolStorage[1].Value,
                "CheckJoinInProgress rejected ReturnValue mismatch");
        Require(observation.RedactedCount == 1,
                "CheckJoinInProgress rejected redacted count mismatch");
        Require(std::strcmp(Observer::LifecycleFieldName(observation.RedactedStorage[0]),
                            "NewPlayer") == 0,
                "CheckJoinInProgress rejected redacted field log token mismatch");
        Require(observation.RedactedProcessLocalSubjectTokens[0] == 0,
                "CheckJoinInProgress rejected retained a private subject token");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "CheckJoinInProgress rejected event-view data rejected");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            CheckJoinInProgressInvocation(1, 0),
            "CheckJoinInProgress rejected evidence copied as diagnostic-only material");

        for (const auto [isFromLogin, returnValue] : {
                 std::pair<uint8_t, uint8_t>{1, 1},
                 std::pair<uint8_t, uint8_t>{0, 1},
                 std::pair<uint8_t, uint8_t>{0, 0},
             })
        {
            const LifecycleInvocation diagnosticInvocation =
                CheckJoinInProgressInvocation(isFromLogin, returnValue);
            Require(!Observer::TryBuildCopiedLifecycleObservation(diagnosticInvocation,
                                                                  observation),
                    "CheckJoinInProgress non-rejected shape built accepted evidence");
            Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                        diagnosticInvocation,
                        observation),
                    "CheckJoinInProgress non-rejected shape did not build diagnostic copy");
            RequireNoPlayerPrincipalEventView(
                observation,
                "CheckJoinInProgress non-rejected diagnostic copy built event evidence");
        }
    }

    void TestBuildsOnLogoutObservationWithoutIdentity()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "valid OnLogout observation rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionEnd, "session end role mismatch");
        Require(observation.Action == Observer::PrincipalAction::CandidateInvalidated,
                "candidate invalidated action mismatch");
        Require(observation.BoolCount == 0, "OnLogout copied bools");
        Require(observation.RedactedCount == 1, "OnLogout redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::Exiting, "OnLogout redacted field mismatch");
    }

    void TestRedactedObjectFieldsCarryPrivateSubjectTokenWithoutRange()
    {
        constexpr uintptr_t privateSubjectPointer = 0x12345000;

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        WriteAt(fixture.Params, 0x00, privateSubjectPointer);
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt startAttempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                        kHandleNewPlayerNameIndex,
                                                                        fixture.Reader(),
                                                                        fixture.Function.data(),
                                                                        fixture.Params.data(),
                                                                        counter,
                                                                        observationNumber);
        Require(startAttempt.Status == Observer::AttemptStatus::Matched,
                "private subject HandleNewPlayer fixture did not match");
        const auto& startField = startAttempt.Invocation.Fields[0];
        Require(startField.Field == LifecycleField::NewPlayer,
                "private subject start field mismatch");
        Require(startField.Redacted && !startField.ExposesRange && startField.Range.Data == nullptr,
                "private subject start field exposed an object range");
        Require(startField.ProcessLocalSubjectToken != 0,
                "private subject start field did not receive an internal token");

        Observer::CopiedLifecycleObservation startObservation;
        Require(Observer::TryBuildCopiedLifecycleObservation(startAttempt.Invocation, startObservation),
                "private subject start observation did not build");
        Require(startObservation.RedactedProcessLocalSubjectTokens[0] ==
                    startField.ProcessLocalSubjectToken,
                "private subject start observation did not copy internal token");
        Require(startObservation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                    startObservation.RedactedProcessLocalSubjectTokens[2] == 0,
                "private subject start observation copied unused object-field tokens");

        BuildObservedOnLogoutFunction(fixture);
        WriteAt(fixture.Params, 0x00, privateSubjectPointer);
        counter.store(0, std::memory_order_relaxed);
        observationNumber = 0;
        Observer::Attempt endAttempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                      kOnLogoutNameIndex,
                                                                      fixture.Reader(),
                                                                      fixture.Function.data(),
                                                                      fixture.Params.data(),
                                                                      counter,
                                                                      observationNumber);
        Require(endAttempt.Status == Observer::AttemptStatus::Matched,
                "private subject OnLogout fixture did not match");
        const auto& endField = endAttempt.Invocation.Fields[0];
        Require(endField.Field == LifecycleField::Exiting,
                "private subject end field mismatch");
        Require(endField.Redacted && !endField.ExposesRange && endField.Range.Data == nullptr,
                "private subject end field exposed an object range");
        Require(endField.ProcessLocalSubjectToken == startField.ProcessLocalSubjectToken,
                "private subject end field did not reuse the internal token");

        Observer::CopiedLifecycleObservation endObservation;
        Require(Observer::TryBuildCopiedLifecycleObservation(endAttempt.Invocation, endObservation),
                "private subject end observation did not build");
        Require(endObservation.RedactedProcessLocalSubjectTokens[0] ==
                    startObservation.RedactedProcessLocalSubjectTokens[0],
                "private subject end observation did not copy matching internal token");
    }

    void TestAcceptsLifecyclePropertyFNameDriftWithRequiredShape()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "seed accepted HandleNewPlayer observation rejected");
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1),
                    observation),
                "exact-shape HandleNewPlayer property FName drift was rejected");
        Require(observation.Role == Observer::LifecycleRole::SessionStart,
                "HandleNewPlayer drift session role mismatch");
        Require(observation.Action == Observer::PrincipalAction::CandidateCreated,
                "HandleNewPlayer drift action mismatch");
        Require(observation.BoolCount == 2,
                "HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "HandleNewPlayer drift did not build internal event view from copied bools");

        Observer::Attempt attempt;
        attempt.Status = Observer::AttemptStatus::Matched;
        attempt.Result = ReadResult::Ok();
        attempt.Invocation = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "matched attempt with exact-shape property FName drift was rejected");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "matched HandleNewPlayer drift attempt did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokHandleNewPlayerPostRestartDriftInvocation(1, 1),
                    observation),
                "post-restart HandleNewPlayer property FName drift was rejected");
        Require(observation.BoolCount == 2,
                "post-restart HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "post-restart HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "post-restart HandleNewPlayer drift did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokHandleNewPlayerRestart20260606DriftInvocation(1, 1),
                    observation),
                "2026-06-06 HandleNewPlayer property FName drift was rejected");
        Require(observation.BoolCount == 2,
                "2026-06-06 HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "2026-06-06 HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "2026-06-06 HandleNewPlayer drift did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokHandleNewPlayerRestart20260607DriftInvocation(1, 1),
                    observation),
                "2026-06-07 HandleNewPlayer property FName drift was rejected");
        Require(observation.BoolCount == 2,
                "2026-06-07 HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "2026-06-07 HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "2026-06-07 HandleNewPlayer drift did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    CurrentRuntimeHandleNewPlayerDriftInvocation(1, 1),
                    observation),
                "current runtime HandleNewPlayer property FName drift was rejected");
        Require(observation.BoolCount == 2,
                "current runtime HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "current runtime HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "current runtime HandleNewPlayer drift did not build internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedTheIslandCheckJoinInProgress20260607DriftInvocation(1, 0),
                    observation),
                "TheIsland CheckJoinInProgress property FName drift was rejected");
        Require(observation.BoolCount == 2,
                "TheIsland CheckJoinInProgress drift bool count mismatch");
        Require(observation.RedactedCount == 1,
                "TheIsland CheckJoinInProgress drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "TheIsland CheckJoinInProgress drift did not build internal event view");

        LifecycleInvocation mixedNewDrift =
            ObservedRagnarokHandleNewPlayerRestart20260606DriftInvocation(1, 1);
        mixedNewDrift.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName0;
        mixedNewDrift.PropertyFNameDrifts[0].ObservedNameIndex = kObservedRagnarokHandleNewPlayerPostRestartName0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(mixedNewDrift, observation),
                "mixed 2026-06-06 observed HandleNewPlayer drift variants built copied observation");
        Require(observation.BoolCount == 0,
                "mixed 2026-06-06 observed HandleNewPlayer drift left copied bools");
        Require(observation.RedactedCount == 0,
                "mixed 2026-06-06 observed HandleNewPlayer drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "mixed 2026-06-06 observed HandleNewPlayer drift built internal event view");

        LifecycleInvocation mixedDrift =
            ObservedRagnarokHandleNewPlayerPostRestartDriftInvocation(1, 1);
        mixedDrift.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName0;
        mixedDrift.PropertyFNameDrifts[0].ObservedNameIndex = kObservedRagnarokHandleNewPlayerName0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(mixedDrift, observation),
                "mixed observed HandleNewPlayer drift variants built copied observation");
        Require(observation.BoolCount == 0,
                "mixed observed HandleNewPlayer drift left copied bools");
        Require(observation.RedactedCount == 0,
                "mixed observed HandleNewPlayer drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "mixed observed HandleNewPlayer drift built internal event view");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CheckJoinInProgressInvocation(1, 1),
                    observation),
                "seed CheckJoinInProgress diagnostic observation rejected");
        LifecycleInvocation diagnosticDrift = CheckJoinInProgressInvocation(1, 1);
        diagnosticDrift.PropertyNameIndicesMatched = false;
        diagnosticDrift.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName3;
        diagnosticDrift.PropertyFNameDrifts.push_back({
            0,
            LifecycleField::BIsFromLogin,
            kBIsFromLoginNameIndex,
            kObservedRagnarokHandleNewPlayerName3,
        });
        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(diagnosticDrift, observation),
                "diagnostic property FName drift built copied diagnostic observation");
        Require(observation.BoolCount == 0,
                "diagnostic property FName drift left copied bools");
        Require(observation.RedactedCount == 0,
                "diagnostic property FName drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "diagnostic property FName drift built internal event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "seed OnLogout observation rejected");
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokOnLogoutDriftInvocation(),
                    observation),
                "exact-shape OnLogout property FName drift was rejected");
        Require(observation.BoolCount == 0,
                "OnLogout drift copied bools");
        Require(observation.RedactedCount == 1,
                "OnLogout drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
                "OnLogout drift did not build internal event view");
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedRagnarokOnLogoutDriftInvocation(
                        kObservedRagnarokOnLogoutRestart20260606Name0),
                    observation),
                "2026-06-06 OnLogout property FName drift was rejected");
        Require(observation.BoolCount == 0,
                "2026-06-06 OnLogout drift copied bools");
        Require(observation.RedactedCount == 1,
                "2026-06-06 OnLogout drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "2026-06-06 OnLogout drift did not build internal event view");
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    CurrentRuntimeOnLogoutDriftInvocation(),
                    observation),
                "current runtime OnLogout property FName drift was rejected");
        Require(observation.BoolCount == 0,
                "current runtime OnLogout drift copied bools");
        Require(observation.RedactedCount == 1,
                "current runtime OnLogout drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "current runtime OnLogout drift did not build internal event view");
    }

    void TestRejectsPostRestartRagnarokHandleNewPlayerName28419Drift()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservation(
                    UnapprovedRagnarokHandleNewPlayerPostRestartObserved28419DriftInvocation(1, 1),
                    observation),
                "post-restart Ragnarok HandleNewPlayer 28419 drift built copied evidence");
        Require(observation.BoolCount == 0,
                "post-restart Ragnarok HandleNewPlayer 28419 drift left copied bools");
        Require(observation.RedactedCount == 0,
                "post-restart Ragnarok HandleNewPlayer 28419 drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "post-restart Ragnarok HandleNewPlayer 28419 drift built internal event-view evidence");

        LifecycleReflectionFixture fixture;
        BuildUnapprovedHandleNewPlayerPostRestartObserved28419Function(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        Observer::Gate gate = EnabledGate();
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber,
                                                                   &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "post-restart Ragnarok HandleNewPlayer 28419 drift matched through observer path");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "post-restart Ragnarok HandleNewPlayer 28419 drift did not fail implausibly");
        Require(attempt.Result.Reason.find(
                    "lifecycle_property_FName_mismatch_expected_name_index_28411") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("cause_unapproved_observed_property_FName") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("observed_property_fname_chain=28419.21315.22969.28517.17725") !=
                    std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "post-restart Ragnarok HandleNewPlayer 28419 drift reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "post-restart Ragnarok HandleNewPlayer 28419 drift consumed event budget");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "post-restart Ragnarok HandleNewPlayer 28419 drift reserved approved evidence role");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "post-restart Ragnarok HandleNewPlayer 28419 drift retained invocation material");

        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "post-original post-restart Ragnarok HandleNewPlayer 28419 drift built copied event");
        Require(observation.BoolCount == 0,
                "post-original post-restart Ragnarok HandleNewPlayer 28419 drift left copied bools");
        Require(observation.RedactedCount == 0,
                "post-original post-restart Ragnarok HandleNewPlayer 28419 drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "post-original post-restart Ragnarok HandleNewPlayer 28419 drift built event view");

        Observer::Attempt diagnosticAttempt =
            Observer::TryIdentifyDiagnosticCandidateInvocation(gate,
                                                               kHandleNewPlayerNameIndex,
                                                               fixture.Reader(),
                                                               fixture.Function.data(),
                                                               fixture.Params.data());
        Require(diagnosticAttempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "post-restart Ragnarok HandleNewPlayer 28419 drift entered diagnostic candidate path");
        Require(diagnosticAttempt.Invocation.FunctionNameIndex == -1,
                "post-restart Ragnarok HandleNewPlayer 28419 diagnostic path retained invocation material");
    }

    void TestCurrentRuntimeAnchorFNameDriftUsesSourceBoundShapeAndK2StaysRejectOnly()
    {
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(
                    CurrentRuntimeHandleNewPlayerDriftInvocation(1, 1),
                    observation),
                "current runtime HandleNewPlayer drift rejected source-bound copied observation");
        Require(observation.BoolCount == 2,
                "current runtime HandleNewPlayer drift bool count mismatch");
        Require(observation.RedactedCount == 3,
                "current runtime HandleNewPlayer drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "current runtime HandleNewPlayer drift did not build event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    ObservedTheIslandCheckJoinInProgress20260607DriftInvocation(1, 0),
                    observation),
                "TheIsland CheckJoinInProgress drift rejected source-bound copied observation");
        Require(observation.BoolCount == 2,
                "TheIsland CheckJoinInProgress drift bool count mismatch");
        Require(observation.RedactedCount == 1,
                "TheIsland CheckJoinInProgress drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "TheIsland CheckJoinInProgress drift did not build event view");

        LifecycleInvocation mixedCurrentHandle = CurrentRuntimeHandleNewPlayerDriftInvocation(1, 1);
        mixedCurrentHandle.Fields[0].PropertyNameIndex = kObservedRagnarokHandleNewPlayerName0;
        mixedCurrentHandle.PropertyFNameDrifts[0].ObservedNameIndex = kObservedRagnarokHandleNewPlayerName0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(mixedCurrentHandle, observation),
                "mixed current-runtime and older HandleNewPlayer drift built copied evidence");
        Require(observation.BoolCount == 0,
                "mixed current-runtime HandleNewPlayer drift left copied bools");
        Require(observation.RedactedCount == 0,
                "mixed current-runtime HandleNewPlayer drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "mixed current-runtime HandleNewPlayer drift built event-view evidence");

        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CurrentRuntimeK2PostLoginDriftInvocation(),
                    observation),
                "current runtime K2_PostLogin drift built diagnostic evidence");
        Require(observation.BoolCount == 0,
                "current runtime K2_PostLogin drift left copied bools");
        Require(observation.RedactedCount == 0,
                "current runtime K2_PostLogin drift left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "current runtime K2_PostLogin drift built event-view evidence");

        Require(Observer::TryBuildCopiedLifecycleObservation(
                    CurrentRuntimeOnLogoutDriftInvocation(),
                    observation),
                "current runtime OnLogout drift rejected source-bound copied observation");
        Require(observation.BoolCount == 0,
                "current runtime OnLogout drift copied bools");
        Require(observation.RedactedCount == 1,
                "current runtime OnLogout drift redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "current runtime OnLogout drift did not build event view");

        Observer::Gate gate = EnabledGate();
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;

        LifecycleReflectionFixture fixture;
        BuildCurrentRuntimeHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber,
                                                                   &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "current runtime HandleNewPlayer drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result),
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "current runtime HandleNewPlayer drift reserved approved evidence before apply");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "current runtime HandleNewPlayer drift consumed event budget before apply");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "current runtime HandleNewPlayer drift reserved the session_start approved role before apply");
        Require(attempt.Invocation.FunctionNameIndex == kHandleNewPlayerNameIndex,
                "current runtime HandleNewPlayer drift did not retain matched invocation material");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          attempt,
                                                                          observation),
                "post-original current runtime HandleNewPlayer drift did not build copied observation");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "post-original current runtime HandleNewPlayer drift did not build event view");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "post-apply current runtime HandleNewPlayer drift did not reserve approved log budget");
        Require(observationNumber == 1,
                "post-apply current runtime HandleNewPlayer drift did not reserve sequence 1");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "post-apply current runtime HandleNewPlayer drift did not consume event budget");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "post-apply current runtime HandleNewPlayer drift did not reserve the session_start approved role");

        counter.store(0, std::memory_order_relaxed);
        roleMask.store(0, std::memory_order_relaxed);
        observationNumber = 99;
        BuildCurrentRuntimeHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        const FNameValue mixedOldApprovedName{kObservedRagnarokHandleNewPlayerName0, 0};
        WriteAt(fixture.PropertyA, 0x18, mixedOldApprovedName);
        attempt = Observer::TryObserveInvocation(gate,
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber,
                                                 &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "mixed current-runtime and older HandleNewPlayer drift matched through observer path");
        Require(attempt.Result.Status == ReadStatus::Implausible,
                "mixed current-runtime HandleNewPlayer drift did not fail implausibly");
        Require(attempt.Result.Reason.find("lifecycle_property_FName_mismatch") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") == std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "mixed current-runtime HandleNewPlayer drift reserved an event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "mixed current-runtime HandleNewPlayer drift consumed event budget");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "mixed current-runtime HandleNewPlayer drift reserved approved evidence role");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "mixed current-runtime HandleNewPlayer drift retained invocation material");
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                           attempt,
                                                                           observation),
                "post-original mixed current-runtime HandleNewPlayer drift built copied evidence");
        RequireNoPlayerPrincipalEventView(
            observation,
            "post-original mixed current-runtime HandleNewPlayer drift built event-view evidence");

        BuildCurrentRuntimeK2PostLoginFunction(fixture);
        Observer::Attempt diagnosticAttempt =
            Observer::TryIdentifyDiagnosticCandidateInvocation(gate,
                                                               kGameModeK2PostLoginNameIndex,
                                                               fixture.Reader(),
                                                               fixture.Function.data(),
                                                               fixture.Params.data());
        Require(diagnosticAttempt.Status == Observer::AttemptStatus::Rejected,
                "current runtime K2_PostLogin drift matched diagnostic candidate path");
        Require(diagnosticAttempt.Result.Status == ReadStatus::Implausible,
                "current runtime K2_PostLogin drift did not fail implausibly");
        RequireCurrentRuntimeOfflineSourceDiagnostic(diagnosticAttempt.Result.Reason,
                                                    "GameMode.K2_PostLogin",
                                                    "28411",
                                                    "28422");
        Require(diagnosticAttempt.Result.Reason.find("lifecycle_property_FName_drift") ==
                    std::string::npos,
                diagnosticAttempt.Result.Reason.c_str());
        Require(diagnosticAttempt.Invocation.FunctionNameIndex == -1,
                "current runtime K2_PostLogin drift retained invocation material");

        counter.store(0, std::memory_order_relaxed);
        roleMask.store(0, std::memory_order_relaxed);
        observationNumber = 99;
        BuildObservedOnLogoutFunction(fixture, kCurrentRuntimeOnLogoutObservedName0);
        attempt = Observer::TryObserveInvocation(gate,
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber,
                                                 &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "current runtime OnLogout drift did not match through observer path");
        Require(attempt.Result.Status == ReadStatus::Ok,
                "current runtime OnLogout drift result did not pass");
        Require(attempt.Result.Reason.find("lifecycle_property_FName_drift") != std::string::npos,
                attempt.Result.Reason.c_str());
        Require(observationNumber == 0,
                "current runtime OnLogout drift reserved approved evidence before apply");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "current runtime OnLogout drift consumed event budget before apply");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "current runtime OnLogout drift reserved approved role before apply");
        Require(attempt.Invocation.FunctionNameIndex == kOnLogoutNameIndex,
                "current runtime OnLogout drift lost invocation material");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 1,
                "current runtime OnLogout drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          attempt,
                                                                          observation),
                "post-original current runtime OnLogout drift rejected copied observation");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "post-original current runtime OnLogout drift did not build event view");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "post-apply current runtime OnLogout drift did not reserve approved log budget");
        Require(observationNumber == 1,
                "post-apply current runtime OnLogout drift did not reserve sequence 1");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "post-apply current runtime OnLogout drift did not consume event budget");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 2),
                "post-apply current runtime OnLogout drift approved role mismatch");
    }

    void TestCopiedEventsPreserveOnlyCanonicalBoolPayloads()
    {
        std::array<uint8_t, 2> sourceBools{1, 1};
        LifecycleInvocation invocation = HandleNewPlayerInvocation(sourceBools[0], sourceBools[1]);

        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "canonical bool-only accepted observation rejected");
        sourceBools = {0, 0};
        Require(observation.BoolStorage[0].Value, "accepted observation retained source bIsFromLogin bytes");
        Require(observation.BoolStorage[1].Value, "accepted observation retained source ReturnValue bytes");
        RequirePlayerPrincipalEventView(observation,
                                        Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                                        Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                                        2,
                                        "bool-only accepted observation did not build an event view");

        uint8_t forgedBool = 1;
        invocation = HandleNewPlayerInvocation(1, 1);
        invocation.Fields[3].Range = {&forgedBool, sizeof(forgedBool)};
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer retained forged raw bIsFromLogin range");
        Require(observation.BoolCount == 0, "forged bool range rejection left accepted bools");
        Require(observation.RedactedCount == 0, "forged bool range rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "forged bool range rejection built internal event-view evidence");

        std::array<uint8_t, 8> identityBytes{};
        invocation = HandleNewPlayerInvocation(1, 1);
        invocation.Fields[0].Range = {identityBytes.data(), identityBytes.size()};
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer copied NewPlayer identity bytes");
        Require(observation.BoolCount == 0, "identity-copy rejection left accepted bools");
        Require(observation.RedactedCount == 0, "identity-copy rejection left redactions");

        invocation = HandleNewPlayerInvocation(1, 1);
        invocation.Fields[0].Range = {nullptr, identityBytes.size()};
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer retained forged NewPlayer range size");
        Require(observation.BoolCount == 0, "forged redacted range-size rejection left accepted bools");
        Require(observation.RedactedCount == 0, "forged redacted range-size rejection left redactions");

        invocation = HandleNewPlayerInvocation(1, 1);
        invocation.Fields[0].ProcessLocalSubjectToken = 0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer built start without private subject token");
        Require(observation.BoolCount == 0, "missing start token rejection left bools");
        Require(observation.RedactedCount == 0, "missing start token rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "missing start token rejection built internal event-view evidence");

        invocation = HandleNewPlayerInvocation(1, 1);
        invocation.Fields[0].ProcessLocalSubjectToken = std::numeric_limits<uint64_t>::max();
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer copied validate-only start token sentinel");
        Require(observation.BoolCount == 0, "start sentinel rejection left bools");
        Require(observation.RedactedCount == 0, "start sentinel rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "start sentinel rejection built internal event-view evidence");

        std::array<uint8_t, 8> textLikeBytes{'p', 'l', 'a', 'y', 'e', 'r', 0, 0};
        invocation = OnLogoutInvocation();
        invocation.Fields[0].Range = {textLikeBytes.data(), textLikeBytes.size()};
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer copied text-like Exiting bytes");
        Require(observation.BoolCount == 0, "text-copy rejection left accepted bools");
        Require(observation.RedactedCount == 0, "text-copy rejection left redactions");

        invocation = OnLogoutInvocation();
        invocation.Fields[0].ProcessLocalSubjectToken = 0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer built logout without private subject token");
        Require(observation.BoolCount == 0, "missing logout token rejection left bools");
        Require(observation.RedactedCount == 0, "missing logout token rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "missing logout token rejection built internal event-view evidence");

        invocation = OnLogoutInvocation();
        invocation.Fields[0].ProcessLocalSubjectToken = std::numeric_limits<uint64_t>::max();
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer copied validate-only logout token sentinel");
        Require(observation.BoolCount == 0, "logout sentinel rejection left bools");
        Require(observation.RedactedCount == 0, "logout sentinel rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "logout sentinel rejection built internal event-view evidence");

        invocation = OnLogoutInvocation();
        invocation.HasParameterRanges = false;
        Require(!Observer::TryBuildCopiedLifecycleObservation(invocation, observation),
                "accepted observer built logout without parameter-backed evidence");
        Require(observation.BoolCount == 0, "missing logout params rejection left bools");
        Require(observation.RedactedCount == 0, "missing logout params rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "missing logout params rejection built internal event-view evidence");

        invocation = CheckJoinInProgressInvocation(1, 1);
        invocation.Fields[1].Range = {identityBytes.data(), identityBytes.size()};
        Require(!Observer::TryBuildCopiedLifecycleDiagnosticObservation(invocation, observation),
                "diagnostic copy retained NewPlayer identity bytes");
        Require(observation.BoolCount == 0, "diagnostic identity-copy rejection left bools");
        Require(observation.RedactedCount == 0, "diagnostic identity-copy rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "diagnostic identity-copy rejection built internal event-view evidence");
    }

    void TestObservedFNameDriftCanBuildPostOriginalCopiedEventViews()
    {
        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 0;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "observed HandleNewPlayer drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 1, "observed HandleNewPlayer drift sequence mismatch");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "observed HandleNewPlayer drift did not reserve one observation");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "observed HandleNewPlayer drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 5,
                "observed HandleNewPlayer drift metadata count mismatch");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(false, attempt, observation),
                "pre-original observed HandleNewPlayer drift built copied event");
        Require(observation.BoolCount == 0, "pre-original observed drift left copied bools");
        Require(observation.RedactedCount == 0, "pre-original observed drift left redactions");

        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original observed HandleNewPlayer drift did not build copied event");
        Require(observation.BoolCount == 2, "observed HandleNewPlayer copied bool count mismatch");
        Require(observation.RedactedCount == 3, "observed HandleNewPlayer redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "observed HandleNewPlayer drift did not produce event-view data");

        BuildObservedHandleNewPlayerPostRestartFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "post-restart observed HandleNewPlayer drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 2,
                "post-restart observed HandleNewPlayer drift sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "post-restart observed HandleNewPlayer drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 5,
                "post-restart observed HandleNewPlayer drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-restart observed HandleNewPlayer drift did not build copied event");
        Require(observation.BoolCount == 2,
                "post-restart observed HandleNewPlayer copied bool count mismatch");

        BuildObservedHandleNewPlayerRestart20260606Function(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "2026-06-06 observed HandleNewPlayer drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 3,
                "2026-06-06 observed HandleNewPlayer drift sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "2026-06-06 observed HandleNewPlayer drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 5,
                "2026-06-06 observed HandleNewPlayer drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "2026-06-06 observed HandleNewPlayer drift did not build copied event");
        Require(observation.BoolCount == 2,
                "2026-06-06 observed HandleNewPlayer copied bool count mismatch");

        BuildObservedHandleNewPlayerRestart20260607Function(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "2026-06-07 observed HandleNewPlayer drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 4,
                "2026-06-07 observed HandleNewPlayer drift sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "2026-06-07 observed HandleNewPlayer drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 5,
                "2026-06-07 observed HandleNewPlayer drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "2026-06-07 observed HandleNewPlayer drift did not build copied event");
        Require(observation.BoolCount == 2,
                "2026-06-07 observed HandleNewPlayer copied bool count mismatch");

        BuildObservedOnLogoutFunction(fixture);
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "observed OnLogout drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(observationNumber == 5, "observed OnLogout drift sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "observed OnLogout drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 1,
                "observed OnLogout drift metadata count mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original observed OnLogout drift did not build copied event");
        Require(observation.BoolCount == 0, "observed OnLogout copied bools");
        Require(observation.RedactedCount == 1, "observed OnLogout redacted count mismatch");
        Require(observation.RedactedStorage[0] == LifecycleField::Exiting,
                "observed OnLogout redacted field mismatch");

        BuildObservedOnLogoutFunction(fixture, kObservedRagnarokOnLogoutPostRestartName0);
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "post-restart observed OnLogout drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "post-restart observed OnLogout drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 1,
                "post-restart observed OnLogout drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original post-restart observed OnLogout drift did not build copied event");
        Require(observation.BoolCount == 0, "post-restart observed OnLogout copied bools");
        Require(observation.RedactedCount == 1,
                "post-restart observed OnLogout redacted count mismatch");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "observed OnLogout drift did not produce event-view data");

        BuildObservedOnLogoutFunction(fixture, kObservedRagnarokOnLogoutRestart20260606Name0);
        observationNumber = 0;
        attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "2026-06-06 observed OnLogout drift did not match through observer path");
        Require(static_cast<bool>(attempt.Result), attempt.Result.Reason.c_str());
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "2026-06-06 observed OnLogout drift reported exact property names");
        Require(attempt.Invocation.PropertyFNameDrifts.size() == 1,
                "2026-06-06 observed OnLogout drift metadata count mismatch");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original 2026-06-06 observed OnLogout drift did not build copied event");
        Require(observation.BoolCount == 0, "2026-06-06 observed OnLogout copied bools");
        Require(observation.RedactedCount == 1,
                "2026-06-06 observed OnLogout redacted count mismatch");
    }

    void TestDiagnosticBudgetAndExactShapeDriftDoNotHideAcceptedEventTriplets()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "diagnostic budget drift test gate was not enabled");

        std::atomic<uint64_t> diagnosticCounter{gate.LogLimit};
        uint64_t diagnosticNumber = 99;
        Require(!Observer::TryReserveObservationBudget(diagnosticCounter, gate.LogLimit, diagnosticNumber),
                "exhausted diagnostic budget reserved a candidate line");
        Require(diagnosticNumber == 0, "exhausted diagnostic budget left a candidate sequence");

        LifecycleReflectionFixture fixture;
        std::atomic<uint64_t> acceptedCounter{0};
        uint64_t observationNumber = 0;

        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   acceptedCounter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "diagnostic budget exhaustion hid drifted session_start match");
        Require(observationNumber == 1, "session_start accepted sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "session_start drift fixture reported exact property names");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                               Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                               2,
                               "diagnostic budget exhaustion hid session_start event semantics");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            attempt.Invocation,
            "drifted session_start copied as a diagnostic candidate");

        BuildCheckJoinInProgressFunction(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;
        attempt = Observer::TryObserveInvocation(gate,
                                                 kCheckJoinInProgressNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "diagnostic budget exhaustion hid CheckJoinInProgress session_start_rejected match");
        Require(observationNumber == 2, "session_start_rejected accepted sequence mismatch");
        Require(attempt.Invocation.PropertyNameIndicesMatched,
                "CheckJoinInProgress rejected-start fixture reported drifted property names");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                               Obelisk::Core::PlayerPrincipalAction::None,
                               2,
                               "diagnostic budget exhaustion hid CheckJoinInProgress session_start_rejected event semantics");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            attempt.Invocation,
            "CheckJoinInProgress session_start_rejected copied as a diagnostic candidate");

        BuildObservedOnLogoutFunction(fixture);
        attempt = Observer::TryObserveInvocation(gate,
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "diagnostic budget exhaustion hid drifted session_end match");
        Require(observationNumber == 3, "session_end accepted sequence mismatch");
        Require(!attempt.Invocation.PropertyNameIndicesMatched,
                "session_end drift fixture reported exact property names");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                               Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                               0,
                               "diagnostic budget exhaustion hid session_end event semantics");
        RequireNoDiagnosticObservationForAcceptedInvocation(
            attempt.Invocation,
            "drifted session_end copied as a diagnostic candidate");

        Require(acceptedCounter.load(std::memory_order_relaxed) == 3,
                "accepted observer budget did not track the three event triplets");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == gate.LogLimit,
                "accepted observer events changed diagnostic candidate budget");
    }

    void TestRejectedAcceptedTargetsCannotExhaustFixedTripletBudget()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "accepted-target reject budget test gate was not enabled");

        std::atomic<uint64_t> diagnosticCounter{gate.LogLimit};
        Require(!Observer::HasObservationBudgetRemaining(diagnosticCounter, gate.LogLimit),
                "diagnostic budget was not exhausted for reject budget test");

        MemoryReader rejectingReader{ThrowingReader, nullptr};
        std::atomic<uint64_t> acceptedCounter{0};
        for (uint64_t i = 0; i < gate.LogLimit; ++i)
        {
            uint64_t rejectedNumber = 99;
            Observer::Attempt rejectedAttempt = Observer::TryObserveInvocation(
                gate,
                kHandleNewPlayerNameIndex,
                rejectingReader,
                reinterpret_cast<void*>(0x10000),
                nullptr,
                acceptedCounter,
                rejectedNumber);
            Require(rejectedAttempt.Status == Observer::AttemptStatus::Rejected,
                    "accepted-target reflection reject did not fail closed");
            Require(rejectedNumber == 0,
                    "accepted-target reflection reject reserved accepted event sequence");
            Require(acceptedCounter.load(std::memory_order_relaxed) == 0,
                    "accepted-target reflection rejects consumed accepted event budget");

            Observer::CopiedLifecycleObservation rejectedObservation;
            Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(
                        true,
                        rejectedAttempt,
                        rejectedObservation),
                    "accepted-target reflection reject built copied event evidence");
            RequireNoPlayerPrincipalEventView(
                rejectedObservation,
                "accepted-target reflection reject built internal event-view evidence");
        }

        LifecycleReflectionFixture fixture;
        uint64_t observationNumber = 0;

        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   acceptedCounter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "fixed HandleNewPlayer session_start view was hidden by prior rejects");
        Require(observationNumber == 1, "fixed session_start sequence was not first accepted event");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                               Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                               2,
                               "fixed session_start event view was not accepted");

        BuildCheckJoinInProgressFunction(fixture);
        fixture.Params[0x00] = 1;
        fixture.Params[0x10] = 0;
        attempt = Observer::TryObserveInvocation(gate,
                                                 kCheckJoinInProgressNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "fixed CheckJoinInProgress session_start_rejected view was hidden by prior rejects");
        Require(observationNumber == 2, "fixed session_start_rejected sequence mismatch");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                               Obelisk::Core::PlayerPrincipalAction::None,
                               2,
                               "fixed session_start_rejected event view was not accepted");

        BuildObservedOnLogoutFunction(fixture);
        attempt = Observer::TryObserveInvocation(gate,
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "fixed OnLogout session_end view was hidden by prior rejects");
        Require(observationNumber == 3, "fixed session_end sequence mismatch");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                               Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                               0,
                               "fixed session_end event view was not accepted");

        Require(acceptedCounter.load(std::memory_order_relaxed) == 3,
                "fixed accepted triplet did not consume exactly three event budget slots");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == gate.LogLimit,
                "fixed accepted triplet changed diagnostic budget");
    }

    template <typename Mutate>
    void RequireObservedHandleDriftRejectedThroughObserver(Mutate mutate, const char* message)
    {
        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        mutate(fixture);

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected, message);
        Require(observationNumber == 0, "rejected observed drift reserved an accepted event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "rejected observed drift consumed an accepted-target event budget slot");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "rejected observed drift left reflected invocation material");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                message);
        Require(observation.BoolCount == 0, "rejected observed drift left copied bools");
        Require(observation.RedactedCount == 0, "rejected observed drift left redactions");
        RequireNoPlayerPrincipalEventView(observation, "rejected observed drift built event view");
    }

    void TestMalformedObservedFNameDriftCannotBuildPostOriginalCopiedEvents()
    {
        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                const FNameValue permutedName{kPlayerDataNameIndex, 0};
                WriteAt(fixture.PropertyA, 0x18, permutedName);
            },
            "observed HandleNewPlayer drift to another lifecycle property name matched");

        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                const FNameValue unapprovedName{kUnapprovedHandleNewPlayerDriftName0, 0};
                WriteAt(fixture.PropertyA, 0x18, unapprovedName);
            },
            "unapproved HandleNewPlayer drift with exact shape matched");

        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                const FNameValue name0{kUnapprovedRagnarokHandleNewPlayerObserved28416Name0, 0};
                const FNameValue name1{kUnapprovedRagnarokHandleNewPlayerObserved28416Name1, 0};
                const FNameValue name2{kUnapprovedRagnarokHandleNewPlayerObserved28416Name2, 0};
                const FNameValue name3{kUnapprovedRagnarokHandleNewPlayerObserved28416Name3, 0};
                const FNameValue name4{kUnapprovedRagnarokHandleNewPlayerObserved28416Name4, 0};
                WriteAt(fixture.PropertyA, 0x18, name0);
                WriteAt(fixture.PropertyB, 0x18, name1);
                WriteAt(fixture.PropertyC, 0x18, name2);
                WriteAt(fixture.PropertyD, 0x18, name3);
                WriteAt(fixture.PropertyE, 0x18, name4);
            },
            "Ragnarok HandleNewPlayer observed 28416 drift matched accepted evidence");

        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                const FNameValue exactName{kNewPlayerNameIndex, 0};
                WriteAt(fixture.PropertyA, 0x18, exactName);
            },
            "mixed exact and observed HandleNewPlayer drift matched");

        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                BuildReorderedObservedHandleNewPlayerFunction(fixture);
            },
            "reordered observed HandleNewPlayer drift matched");

        RequireObservedHandleDriftRejectedThroughObserver(
            [](LifecycleReflectionFixture& fixture) {
                WriteAt(fixture.PropertyD, 0x72, uint8_t{0xff});
            },
            "observed HandleNewPlayer drift with bad bool metadata matched");

        Observer::Attempt identityAttempt;
        identityAttempt.Status = Observer::AttemptStatus::Matched;
        identityAttempt.Result = ReadResult::Ok();
        identityAttempt.Invocation = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        uint8_t leakedObjectBytes[8] = {};
        identityAttempt.Invocation.Fields[0].Range = {leakedObjectBytes, sizeof(leakedObjectBytes)};

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(
                    true,
                    identityAttempt,
                    observation),
                "identity-exposing observed HandleNewPlayer drift built copied event");
        Require(observation.BoolCount == 0, "identity-exposing observed drift left copied bools");
        Require(observation.RedactedCount == 0, "identity-exposing observed drift left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "identity-exposing observed drift built event view");

        identityAttempt.Invocation = ObservedRagnarokOnLogoutDriftInvocation();
        identityAttempt.Invocation.Fields[0].Range = {leakedObjectBytes, sizeof(leakedObjectBytes)};
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(
                    true,
                    identityAttempt,
                    observation),
                "identity-exposing observed OnLogout drift built copied event");
        Require(observation.BoolCount == 0, "identity-exposing OnLogout drift left copied bools");
        Require(observation.RedactedCount == 0, "identity-exposing OnLogout drift left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "identity-exposing OnLogout drift built event view");

        LifecycleReflectionFixture fixture;
        BuildObservedOnLogoutFunction(fixture);
        const FNameValue unapprovedLogoutName{kUnapprovedOnLogoutDriftName0, 0};
        WriteAt(fixture.PropertyA, 0x18, unapprovedLogoutName);

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(EnabledGate(),
                                                                   kOnLogoutNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "unapproved OnLogout drift with exact shape matched");
        Require(observationNumber == 0, "unapproved OnLogout drift reserved event sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "unapproved OnLogout drift consumed accepted event budget");
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "unapproved OnLogout drift built copied event");
        RequireNoPlayerPrincipalEventView(observation,
                                          "unapproved OnLogout drift built event view");
    }

    void TestAcceptedTargetMismatchesRemainNonEvidenceUntilObserverEventBuilds()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "accepted-target mismatch test gate was not enabled");

        LifecycleReflectionFixture fixture;
        std::atomic<uint64_t> acceptedCounter{0};
        uint64_t observationNumber = 0;

        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        const FNameValue permutedName{kPlayerDataNameIndex, 0};
        WriteAt(fixture.PropertyA, 0x18, permutedName);

        Observer::Attempt diagnosticAttempt =
            Observer::TryIdentifyDiagnosticCandidateInvocation(gate,
                                                               kHandleNewPlayerNameIndex,
                                                               fixture.Reader(),
                                                               fixture.Function.data(),
                                                               fixture.Params.data());
        Require(diagnosticAttempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "HandleNewPlayer diagnostic candidate path consumed accepted-target mismatch");
        Require(diagnosticAttempt.Invocation.FunctionNameIndex == -1,
                "HandleNewPlayer diagnostic path left reflected invocation material");

        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   acceptedCounter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "HandleNewPlayer accepted-target mismatch was not rejected");
        Require(observationNumber == 0, "HandleNewPlayer mismatch reserved accepted event sequence");
        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "HandleNewPlayer accepted-target mismatch built copied evidence");
        Require(observation.BoolCount == 0, "HandleNewPlayer mismatch left copied bools");
        Require(observation.RedactedCount == 0, "HandleNewPlayer mismatch left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "HandleNewPlayer mismatch built internal event-view evidence");

        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;
        attempt = Observer::TryObserveInvocation(gate,
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "HandleNewPlayer accepted path did not recover after mismatch");
        Require(observationNumber == 1, "HandleNewPlayer accepted sequence mismatch after rejection");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                               Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                               2,
                               "HandleNewPlayer accepted event did not build after mismatch");

        BuildObservedOnLogoutFunction(fixture);
        WriteAt(fixture.PropertyA, 0x4c, int32_t{0x04});
        diagnosticAttempt = Observer::TryIdentifyDiagnosticCandidateInvocation(gate,
                                                                              kOnLogoutNameIndex,
                                                                              fixture.Reader(),
                                                                              fixture.Function.data(),
                                                                              fixture.Params.data());
        Require(diagnosticAttempt.Status == Observer::AttemptStatus::NonLifecycleFunction,
                "OnLogout diagnostic candidate path consumed accepted-target mismatch");
        Require(diagnosticAttempt.Invocation.FunctionNameIndex == -1,
                "OnLogout diagnostic path left reflected invocation material");

        attempt = Observer::TryObserveInvocation(gate,
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "OnLogout accepted-target mismatch was not rejected");
        Require(observationNumber == 0, "OnLogout mismatch reserved accepted event sequence");
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "OnLogout accepted-target mismatch built copied evidence");
        Require(observation.BoolCount == 0, "OnLogout mismatch left copied bools");
        Require(observation.RedactedCount == 0, "OnLogout mismatch left redactions");
        RequireNoPlayerPrincipalEventView(observation,
                                          "OnLogout mismatch built internal event-view evidence");

        BuildObservedOnLogoutFunction(fixture);
        attempt = Observer::TryObserveInvocation(gate,
                                                 kOnLogoutNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 acceptedCounter,
                                                 observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "OnLogout accepted path did not recover after mismatch");
        Require(observationNumber == 2, "OnLogout accepted sequence mismatch after rejection");
        RequireCopiedEventView(attempt,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                               Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                               0,
                               "OnLogout accepted event did not build after mismatch");
    }

    void TestRejectsMalformedLifecyclePropertyFNameDriftObservations()
    {
        Observer::CopiedLifecycleObservation observation;
        uint8_t leakedObjectBytes[8] = {};

        LifecycleInvocation malformed = CheckJoinInProgressInvocation(1, 0);
        std::swap(malformed.Fields[0], malformed.Fields[2]);
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "order-mismatched exact CheckJoinInProgress 1,0 built observation");
        Require(observation.BoolCount == 0, "order-mismatched CheckJoin left copied bools");
        Require(observation.RedactedCount == 0, "order-mismatched CheckJoin left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "order-mismatched exact CheckJoinInProgress 1,0 built event view");

        malformed = CheckJoinInProgressInvocation(1, 0);
        malformed.PropertyNameIndicesMatched = false;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "stale-drift exact CheckJoinInProgress 1,0 built observation");
        Require(observation.BoolCount == 0, "stale-drift CheckJoin left copied bools");
        Require(observation.RedactedCount == 0, "stale-drift CheckJoin left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "stale-drift exact CheckJoinInProgress 1,0 built event view");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.Fields[0].Offset = 0x04;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift with wrong redacted object offset built observation");
        Require(observation.BoolCount == 0, "wrong offset drift left copied bools");
        Require(observation.RedactedCount == 0, "wrong offset drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        std::swap(malformed.Fields[0], malformed.Fields[1]);
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift with reordered fields built observation");
        Require(observation.BoolCount == 0, "reordered drift left copied bools");
        Require(observation.RedactedCount == 0, "reordered drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.Fields[0].Range = {leakedObjectBytes, sizeof(leakedObjectBytes)};
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift with exposed object identity built observation");
        Require(observation.BoolCount == 0, "identity-leaking drift left copied bools");
        Require(observation.RedactedCount == 0, "identity-leaking drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.PropertyFNameDrifts[0].ObservedNameIndex = kObservedRagnarokHandleNewPlayerName1;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift with mismatched drift metadata built observation");
        Require(observation.BoolCount == 0, "mismatched drift metadata left copied bools");
        Require(observation.RedactedCount == 0, "mismatched drift metadata left redactions");

        malformed = ObservedRagnarokHandleNewPlayerPostRestartDriftInvocation(1, 1);
        std::swap(malformed.PropertyFNameDrifts[0].Position, malformed.PropertyFNameDrifts[1].Position);
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer post-restart drift with permuted drift positions built observation");
        Require(observation.BoolCount == 0, "permuted drift positions left copied bools");
        Require(observation.RedactedCount == 0, "permuted drift positions left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.Fields[0].PropertyNameIndex = kUnapprovedHandleNewPlayerDriftName0;
        malformed.PropertyFNameDrifts[0].ObservedNameIndex = kUnapprovedHandleNewPlayerDriftName0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer unapproved drift name built observation");
        Require(observation.BoolCount == 0, "unapproved drift name left copied bools");
        Require(observation.RedactedCount == 0, "unapproved drift name left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.Fields[0].PropertyNameIndex = kNewPlayerNameIndex;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "mixed exact and observed HandleNewPlayer drift built observation");
        Require(observation.BoolCount == 0, "mixed exact drift left copied bools");
        Require(observation.RedactedCount == 0, "mixed exact drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.Fields[0].PropertyNameIndex = kPlayerDataNameIndex;
        malformed.PropertyFNameDrifts[0].ObservedNameIndex = kPlayerDataNameIndex;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift to another lifecycle property name built observation");
        Require(observation.BoolCount == 0, "permuted property name drift left copied bools");
        Require(observation.RedactedCount == 0, "permuted property name drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.PropertyFNameDrifts[4].Position = 5;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer drift with out-of-bounds drift position built observation");
        Require(observation.BoolCount == 0, "out-of-bounds drift left copied bools");
        Require(observation.RedactedCount == 0, "out-of-bounds drift left redactions");

        malformed = ObservedRagnarokHandleNewPlayerDriftInvocation(1, 1);
        malformed.PropertyNameIndicesMatched = true;
        malformed.PropertyFNameDrifts.clear();
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "HandleNewPlayer observed property names without drift records built observation");
        Require(observation.BoolCount == 0, "missing drift records left copied bools");
        Require(observation.RedactedCount == 0, "missing drift records left redactions");

        malformed = ObservedRagnarokOnLogoutDriftInvocation();
        malformed.Fields[0].PropertyNameIndex = kUnapprovedOnLogoutDriftName0;
        malformed.PropertyFNameDrifts[0].ObservedNameIndex = kUnapprovedOnLogoutDriftName0;
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "OnLogout unapproved drift name built observation");
        Require(observation.BoolCount == 0, "OnLogout unapproved drift left copied bools");
        Require(observation.RedactedCount == 0, "OnLogout unapproved drift left redactions");

        malformed = ObservedRagnarokOnLogoutDriftInvocation();
        malformed.Fields[0].Range = {leakedObjectBytes, sizeof(leakedObjectBytes)};
        Require(!Observer::TryBuildCopiedLifecycleObservation(malformed, observation),
                "OnLogout drift with exposed exiting identity built observation");
        Require(observation.BoolCount == 0, "OnLogout identity leak left copied bools");
        Require(observation.RedactedCount == 0, "OnLogout identity leak left redactions");
    }

    void TestAfterOriginalGuard()
    {
        Observer::Attempt attempt;
        attempt.Status = Observer::AttemptStatus::Matched;
        attempt.Result = ReadResult::Ok();
        attempt.Invocation = HandleNewPlayerInvocation(1, 1);

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(false, attempt, observation),
                "pre-original lifecycle observation accepted");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "post-original lifecycle observation rejected");
    }

    void TestMatchedAttemptRequiresSuccessfulReflectionResult()
    {
        Observer::Attempt attempt;
        attempt.Status = Observer::AttemptStatus::Matched;
        attempt.Result = ReadResult::Fail(ReadStatus::Implausible, "shape was not reflection success");
        attempt.Invocation = HandleNewPlayerInvocation(1, 1);

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "matched attempt with failed reflection result built lifecycle observation");
        Require(observation.BoolCount == 0, "failed reflection result left copied bools");
        Require(observation.RedactedCount == 0, "failed reflection result left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "matched attempt with failed reflection result built internal event view");

        attempt.Result = ReadResult::Ok();
        attempt.Invocation.Fields.clear();
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "matched attempt with malformed copied lifecycle invocation built observation");
        Require(observation.BoolCount == 0, "malformed copied lifecycle invocation left bools");
        Require(observation.RedactedCount == 0, "malformed copied lifecycle invocation left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "malformed copied lifecycle invocation built internal event view");

        attempt.Invocation = HandleNewPlayerInvocation(1, 1);
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "matched attempt with successful reflection result rejected lifecycle observation");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
            Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
            2,
            "successful matched lifecycle attempt did not build internal event view");
    }

    void TestNonMatchedShapeOkAttemptsDoNotBuildLifecycleEvent()
    {
        for (Observer::AttemptStatus status : {
                 Observer::AttemptStatus::Disabled,
                 Observer::AttemptStatus::BudgetExhausted,
                 Observer::AttemptStatus::NonLifecycleFunction,
                 Observer::AttemptStatus::Rejected,
             })
        {
            Observer::Attempt attempt;
            attempt.Status = status;
            attempt.Result = ReadResult::Ok();
            attempt.Invocation = HandleNewPlayerInvocation(1, 1);

            Observer::CopiedLifecycleObservation observation;
            Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                    "non-matched shape-ok attempt built lifecycle event");
            Require(observation.BoolCount == 0, "non-matched shape-ok attempt left bools");
            Require(observation.RedactedCount == 0, "non-matched shape-ok attempt left redactions");
            RequireNoPlayerPrincipalEventView(
                observation,
                "non-matched shape-ok attempt built internal event view");
        }
    }

    void TestDispatchLimitZeroBlocksDispatchBudgetEvenWithShapeOk()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "dispatch-limit-zero gate was not enabled for logging");
        Require(gate.DispatchLimit == 0, "dispatch-limit-zero gate did not retain zero dispatch budget");

        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "shape-ok lifecycle observation fixture rejected");

        std::atomic<uint64_t> dispatchCounter{0};
        uint64_t dispatchNumber = 77;
        Require(!Observer::HasObservationBudgetRemaining(dispatchCounter, gate.DispatchLimit),
                "dispatch limit 0 reported callback/event budget remaining");
        Require(!Observer::TryReserveObservationBudget(dispatchCounter, gate.DispatchLimit, dispatchNumber),
                "dispatch limit 0 reserved callback/event budget for shape-ok observation");
        Require(dispatchNumber == 0, "dispatch limit 0 left callback/event sequence");
        Require(dispatchCounter.load(std::memory_order_relaxed) == 0,
                "dispatch limit 0 incremented callback/event counter");
    }

    void TestApprovedRuntimeEvidenceLogBudgetKeepsOnlyStrictTripletRoles()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "approved runtime log budget gate was not enabled");
        Require(gate.LogLimit == 10, "approved runtime log budget limit mismatch");

        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;
        Observer::CopiedLifecycleObservation observation;

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "accepted start observation did not build for approved log budget test");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == (1u << 0),
                "accepted start did not map to the approved start log role");
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "accepted start did not reserve approved log budget");
        Require(observationNumber == 1, "accepted start reserved wrong approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "accepted start did not advance approved log counter once");

        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "duplicate accepted start reserved approved log budget");
        Require(observationNumber == 0, "duplicate accepted start left approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "duplicate accepted start advanced approved log counter");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "login-backed HandleNewPlayer 1,0 built approved runtime evidence observation");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == 0,
                "HandleNewPlayer 1,0 rejection mapped to approved log role");
        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "HandleNewPlayer 1,0 rejection reserved approved log budget");
        Require(observationNumber == 0, "HandleNewPlayer 1,0 rejection left approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "HandleNewPlayer 1,0 rejection advanced approved log counter");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(
                    CheckJoinInProgressInvocation(1, 1),
                    observation),
                "CheckJoinInProgress diagnostic observation did not build");
        Require(observation.Role == Observer::LifecycleRole::DiagnosticOnly,
                "CheckJoinInProgress diagnostic did not use diagnostic-only role");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == 0,
                "CheckJoinInProgress diagnostic mapped to approved log role");
        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "CheckJoinInProgress diagnostic reserved approved log budget");
        Require(observationNumber == 0, "CheckJoinInProgress diagnostic left approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "CheckJoinInProgress diagnostic advanced approved log counter");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(K2PostLoginInvocation(), observation),
                "K2_PostLogin diagnostic observation did not build");
        Require(observation.Role == Observer::LifecycleRole::DiagnosticOnly,
                "K2_PostLogin diagnostic did not use diagnostic-only role");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == 0,
                "K2_PostLogin diagnostic mapped to approved log role");
        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "K2_PostLogin diagnostic reserved approved log budget");
        Require(observationNumber == 0, "K2_PostLogin diagnostic left approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "K2_PostLogin diagnostic advanced approved log counter");

        Require(Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 0), observation),
                "strict CheckJoin rejected-start observation did not build");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == (1u << 1),
                "strict CheckJoin rejected-start did not map to approved rejected-start log role");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "strict CheckJoin rejected-start did not reserve approved log budget");
        Require(observationNumber == 2, "strict CheckJoin rejected-start reserved wrong sequence");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "session end observation did not build for approved log budget test");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == (1u << 2),
                "session end did not map to approved end log role");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "session end did not reserve approved log budget");
        Require(observationNumber == 3, "session end reserved wrong approved log sequence");
        Require(counter.load(std::memory_order_relaxed) == 3,
                "approved triplet should consume exactly three log slots");

        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "duplicate session end reserved approved log budget");
        Require(counter.load(std::memory_order_relaxed) == 3,
                "duplicate session end advanced approved log counter");
    }

    void TestApprovedRuntimeEvidenceLogBudgetDoesNotInferRejectedRoleFromStartAndEnd()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "approved runtime start/end subset gate was not enabled");

        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;
        Observer::CopiedLifecycleObservation observation;

        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "start/end subset accepted start observation did not build");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == (1u << 0),
                "start/end subset accepted start mapped to the wrong role");
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "start/end subset accepted start did not reserve approved log budget");
        Require(observationNumber == 1,
                "start/end subset accepted start reserved wrong sequence");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "start/end subset session end observation did not build");
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(observation) == (1u << 2),
                "start/end subset session end mapped to the wrong role");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "start/end subset session end did not reserve approved log budget");
        Require(observationNumber == 2,
                "start/end subset session end reserved wrong sequence");

        Require(counter.load(std::memory_order_relaxed) == 2,
                "start/end subset consumed more than two approved log slots");
        Require(roleMask.load(std::memory_order_relaxed) == ((1u << 0) | (1u << 2)),
                "start/end subset reserved an unexpected approved role bit");
        Require((roleMask.load(std::memory_order_relaxed) & (1u << 1)) == 0,
                "start/end subset inferred the missing CheckJoinInProgress rejected-start role");
        Require(roleMask.load(std::memory_order_relaxed) !=
                    ((1u << 0) | (1u << 1) | (1u << 2)),
                "start/end subset was indistinguishable from the complete approved triplet");
    }

    void TestApprovedRuntimeEvidenceLogBudgetWaitsForFinalTokenAssignment()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "approved runtime final-token test gate was not enabled");

        ResetProcessLocalSubjectTokensForTesting();

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;

        SetNextProcessLocalSubjectTokenForTesting(
            std::numeric_limits<uint64_t>::max());
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   fixture.Reader(),
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber,
                                                                   &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "final token exhaustion did not reject the approved start");
        Require(observationNumber == 0,
                "final token exhaustion left an approved observation sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "final token exhaustion consumed approved log budget");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "final token exhaustion burned an approved role bit");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "final token exhaustion built copied lifecycle evidence");
        RequireNoPlayerPrincipalEventView(
            observation,
            "final token exhaustion built internal event-view evidence");

        ResetProcessLocalSubjectTokensForTesting();
        observationNumber = 99;
        attempt = Observer::TryObserveInvocation(gate,
                                                 kHandleNewPlayerNameIndex,
                                                 fixture.Reader(),
                                                 fixture.Function.data(),
                                                 fixture.Params.data(),
                                                 counter,
                                                 observationNumber,
                                                 &roleMask);
        Require(attempt.Status == Observer::AttemptStatus::Matched,
                "approved start did not recover after final token exhaustion");
        Require(observationNumber == 0,
                "recovered approved start reserved before post-apply evidence gate");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "recovered approved start consumed a log slot before post-apply evidence gate");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "recovered approved start set the start role bit before post-apply evidence gate");
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "recovered approved start did not build copied event evidence");
        RequirePlayerPrincipalEventView(observation,
                                        Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                                        Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                                        2,
                                        "recovered approved start did not build copied event evidence");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    observation,
                    gate.LogLimit,
                    observationNumber),
                "recovered approved start did not reserve post-apply log budget");
        Require(observationNumber == 1,
                "recovered approved start reserved the wrong post-apply sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "recovered approved start did not consume one post-apply log slot");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "recovered approved start did not set the post-apply start role bit");

        ResetProcessLocalSubjectTokensForTesting();
    }

    void TestApprovedRuntimeEvidenceLogBudgetDoesNotStarveLifecycleState()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "approved runtime state-starvation test gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        ResetProcessLocalSubjectTokensForTesting();
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;

        Observer::Attempt firstStart = Observer::TryObserveInvocation(gate,
                                                                       kHandleNewPlayerNameIndex,
                                                                       fixture.Reader(),
                                                                       fixture.Function.data(),
                                                                       fixture.Params.data(),
                                                                       counter,
                                                                       observationNumber,
                                                                       &roleMask);
        Require(firstStart.Status == Observer::AttemptStatus::Matched,
                "first approved start did not match");
        Require(observationNumber == 0,
                "first approved start reserved log sequence before post-apply gate");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "first approved start consumed a log slot before post-apply gate");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "first approved start set the start role bit before post-apply gate");
        Observer::CopiedLifecycleObservation firstObservation;
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          firstStart,
                                                                          firstObservation),
                "first approved start did not build event-view state");
        RequirePlayerPrincipalEventView(firstObservation,
                                        Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                                        Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                                        2,
                                        "first approved start did not build event-view state");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    firstObservation,
                    gate.LogLimit,
                    observationNumber),
                "first approved start did not reserve post-apply log budget");
        Require(observationNumber == 1,
                "first approved start did not reserve post-apply log sequence 1");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "first approved start did not consume exactly one post-apply log slot");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "first approved start did not set the post-apply start role bit");

        observationNumber = 99;
        Observer::Attempt duplicateStart = Observer::TryObserveInvocation(gate,
                                                                          kHandleNewPlayerNameIndex,
                                                                          fixture.Reader(),
                                                                          fixture.Function.data(),
                                                                          fixture.Params.data(),
                                                                          counter,
                                                                          observationNumber,
                                                                          &roleMask);
        Require(duplicateStart.Status == Observer::AttemptStatus::Matched,
                "duplicate approved start starved lifecycle state");
        Require(observationNumber == 0,
                "duplicate approved start reserved another evidence log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "duplicate approved start advanced approved log counter");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "duplicate approved start changed approved role bits");
        Observer::CopiedLifecycleObservation duplicateObservation;
        Require(Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true,
                                                                          duplicateStart,
                                                                          duplicateObservation),
                "duplicate approved start did not preserve event-view state");
        RequirePlayerPrincipalEventView(duplicateObservation,
                                        Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                                        Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                                        2,
                                        "duplicate approved start did not preserve event-view state");
        observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    duplicateObservation,
                    gate.LogLimit,
                    observationNumber),
                "duplicate approved start reserved post-apply evidence log budget");
        Require(observationNumber == 0,
                "duplicate approved start left a post-apply evidence log sequence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "duplicate approved start advanced post-apply approved log counter");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "duplicate approved start changed post-apply approved role bits");

        counter.store(gate.LogLimit, std::memory_order_relaxed);
        roleMask.store(0, std::memory_order_relaxed);
        observationNumber = 99;
        Observer::Attempt exhaustedLogStart = Observer::TryObserveInvocation(gate,
                                                                             kHandleNewPlayerNameIndex,
                                                                             fixture.Reader(),
                                                                             fixture.Function.data(),
                                                                             fixture.Params.data(),
                                                                             counter,
                                                                             observationNumber,
                                                                             &roleMask);
        Require(exhaustedLogStart.Status == Observer::AttemptStatus::Matched,
                "exhausted approved log budget starved lifecycle state");
        Require(observationNumber == 0,
                "exhausted approved log budget reserved a log sequence");
        Require(counter.load(std::memory_order_relaxed) == gate.LogLimit,
                "exhausted approved log budget changed counter");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "exhausted approved log budget set a role bit");
        RequireCopiedEventView(exhaustedLogStart,
                               Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                               Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                               2,
                               "exhausted approved log budget did not preserve event-view state");

        ResetProcessLocalSubjectTokensForTesting();
    }

    void TestDiagnosticBudgetExhaustionCannotStarveAcceptedLifecycleBudget()
    {
        Observer::Gate gate = EnabledGate();
        Require(gate.Enabled(), "diagnostic starvation test gate was not enabled");
        Require(gate.LogLimit == 10, "diagnostic starvation test log limit mismatch");
        Require(gate.DispatchLimit == 0, "diagnostic starvation test dispatch limit mismatch");

        std::atomic<uint64_t> diagnosticCounter{gate.LogLimit};
        uint64_t diagnosticNumber = 77;
        Require(!Observer::HasObservationBudgetRemaining(diagnosticCounter, gate.LogLimit),
                "exhausted diagnostic budget reported remaining capacity");
        Require(!Observer::TryReserveObservationBudget(diagnosticCounter, gate.LogLimit, diagnosticNumber),
                "exhausted diagnostic budget reserved another candidate line");
        Require(diagnosticNumber == 0, "exhausted diagnostic budget left a candidate sequence");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == gate.LogLimit,
                "exhausted diagnostic reserve changed diagnostic counter");

        MemoryReader reader{ThrowingReader, nullptr};
        std::atomic<uint64_t> acceptedCounter{0};
        uint64_t acceptedNumber = 99;
        Observer::Attempt rejectedAttempt = Observer::TryObserveInvocation(
            gate,
            kHandleNewPlayerNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            nullptr,
            acceptedCounter,
            acceptedNumber);
        Require(rejectedAttempt.Status == Observer::AttemptStatus::Rejected,
                "accepted lifecycle budget did not reach reflection after diagnostic exhaustion");
        Require(acceptedNumber == 0, "rejected accepted lifecycle attempt reserved an event sequence");
        Require(!Observer::ShouldLogObservation(acceptedNumber, gate.LogLimit),
                "rejected accepted lifecycle attempt was loggable as accepted evidence");
        Require(acceptedCounter.load(std::memory_order_relaxed) == 0,
                "rejected accepted lifecycle attempt consumed accepted event budget");
        Require(diagnosticCounter.load(std::memory_order_relaxed) == gate.LogLimit,
                "accepted lifecycle reserve changed diagnostic counter");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, rejectedAttempt, observation),
                "rejected accepted lifecycle attempt built a copied event");
        Require(observation.BoolCount == 0, "rejected accepted lifecycle attempt left bools");
        Require(observation.RedactedCount == 0, "rejected accepted lifecycle attempt left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "rejected accepted lifecycle attempt built internal event view");

        acceptedCounter.store(gate.LogLimit, std::memory_order_relaxed);
        acceptedNumber = 88;
        Observer::Attempt exhaustedAcceptedAttempt = Observer::TryObserveInvocation(
            gate,
            kHandleNewPlayerNameIndex,
            reader,
            reinterpret_cast<void*>(0x10000),
            nullptr,
            acceptedCounter,
            acceptedNumber);
        Require(exhaustedAcceptedAttempt.Status == Observer::AttemptStatus::BudgetExhausted,
                "exhausted accepted lifecycle budget did not fail closed");
        Require(acceptedNumber == 0, "exhausted accepted lifecycle budget left an event sequence");
        Require(acceptedCounter.load(std::memory_order_relaxed) == gate.LogLimit,
                "exhausted accepted lifecycle budget changed accepted counter");
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(
                    true,
                    exhaustedAcceptedAttempt,
                    observation),
                "exhausted accepted lifecycle budget built a copied event");
        Require(observation.BoolCount == 0, "exhausted accepted lifecycle budget left bools");
        Require(observation.RedactedCount == 0, "exhausted accepted lifecycle budget left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "exhausted accepted lifecycle budget built internal event view");
    }

    void TestBudgetRaceDoesNotReadLifecycleParamPayloads()
    {
        Observer::Gate gate = EnabledGate("1");
        Require(gate.Enabled(), "budget-race lifecycle gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        WriteAt(fixture.Params, 0x00, uintptr_t{0x12345000});
        WriteAt(fixture.Params, 0x08, uintptr_t{0x12346000});
        WriteAt(fixture.Params, 0x10, uintptr_t{0x12347000});
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        (void)fixture.Reader();
        std::atomic<uint64_t> counter{0};
        BudgetRaceReaderContext context{
            .Regions = fixture.Context.Regions,
            .Params = fixture.Params.data(),
            .Counter = &counter,
            .Limit = gate.LogLimit,
            .ExhaustBudgetOnMetadataRead = true,
        };
        MemoryReader reader{BudgetRaceReader, &context};

        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   reader,
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::BudgetExhausted,
                "budget-race accepted lifecycle attempt did not fail closed");
        Require(observationNumber == 0, "budget-race attempt left an observation sequence");
        Require(context.MetadataReads != 0, "budget-race fixture did not reach metadata recognition");
        Require(context.BoolParamReads == 0,
                "budget-race metadata pass copied lifecycle bool payload bytes");
        Require(context.RedactedObjectParamReads == 0,
                "budget-race metadata pass read redacted object correlate bytes");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "budget-race attempt retained reflected invocation material");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "budget-race attempt built copied lifecycle evidence");
        Require(observation.BoolCount == 0, "budget-race attempt left copied bools");
        Require(observation.RedactedCount == 0, "budget-race attempt left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "budget-race attempt built internal event-view evidence");
    }

    void TestMissingSubjectTokenRejectsWithoutBudgetOrCopiedObservation()
    {
        Observer::Gate gate = EnabledGate("1");
        Require(gate.Enabled(), "missing-token lifecycle gate was not enabled");

        LifecycleReflectionFixture fixture;
        BuildObservedHandleNewPlayerFunction(fixture);
        fixture.Params[0x18] = 1;
        fixture.Params[0x19] = 1;

        MemoryReader reader = fixture.Reader();
        fixture.Context.Regions.pop_back();
        fixture.Context.Regions.push_back({fixture.Params.data() + 0x18, 2});

        std::atomic<uint64_t> counter{0};
        uint64_t observationNumber = 99;
        Observer::Attempt attempt = Observer::TryObserveInvocation(gate,
                                                                   kHandleNewPlayerNameIndex,
                                                                   reader,
                                                                   fixture.Function.data(),
                                                                   fixture.Params.data(),
                                                                   counter,
                                                                   observationNumber);
        Require(attempt.Status == Observer::AttemptStatus::Rejected,
                "missing private subject token did not reject before event budget");
        Require(observationNumber == 0, "missing-token rejection left an observation sequence");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "missing-token rejection reserved event budget");
        Require(attempt.Invocation.FunctionNameIndex == -1,
                "missing-token rejection retained reflected invocation material");

        Observer::CopiedLifecycleObservation observation;
        Require(!Observer::TryBuildCopiedLifecycleObservationAfterOriginal(true, attempt, observation),
                "missing-token rejection built copied lifecycle evidence");
        Require(observation.BoolCount == 0, "missing-token rejection left copied bools");
        Require(observation.RedactedCount == 0, "missing-token rejection left redactions");
        RequireNoPlayerPrincipalEventView(
            observation,
            "missing-token rejection built internal event-view evidence");
    }

    void TestBuildsPlayerPrincipalEventViews()
    {
        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd;
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionStart, kind),
                "session start role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                "session start kind mismatch");
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionStartRejected, kind),
                "session start rejected role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                "session start rejected kind mismatch");
        Require(Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::SessionEnd, kind),
                "session end role did not map");
        Require(kind == Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                "session end kind mismatch");
        Require(!Observer::TryMapPlayerPrincipalEventKind(Observer::LifecycleRole::DiagnosticOnly, kind),
                "diagnostic-only role mapped to event kind");
        Require(std::strcmp(Observer::LifecycleRoleName(Observer::LifecycleRole::DiagnosticOnly),
                            "diagnostic_only") == 0,
                "diagnostic-only role token mismatch");

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated;
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::None, action),
                "none action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::None,
                "none action mismatch");
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::CandidateCreated, action),
                "candidate-created action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                "candidate-created action mismatch");
        Require(Observer::TryMapPlayerPrincipalAction(Observer::PrincipalAction::CandidateInvalidated, action),
                "candidate-invalidated action did not map");
        Require(action == Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                "candidate-invalidated action mismatch");

        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "accepted start observation did not build");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Require(Observer::TryBuildPlayerPrincipalEventView(observation, boolStorage, event),
                "accepted start event view did not build");
        Require(event.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                "accepted start event kind mismatch");
        Require(event.Action == Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                "accepted start action mismatch");
        Require(event.Bools.data() == boolStorage.data(), "event did not use caller bool storage");
        Require(event.Bools.size() == 2, "accepted start bool count mismatch");
        Require(event.Bools[0].Field == Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin,
                "accepted start first bool field mismatch");
        Require(event.Bools[0].Value, "accepted start bIsFromLogin mismatch");
        Require(event.Bools[1].Field == Obelisk::Core::PlayerPrincipalBoolField::ReturnValue,
                "accepted start second bool field mismatch");
        Require(event.Bools[1].Value, "accepted start ReturnValue mismatch");

        observation.BoolStorage[0].Value = false;
        Require(event.Bools[0].Value, "event view retained copied observation storage");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "login-backed HandleNewPlayer 1,0 built rejected-start observation");
        RequireNoPlayerPrincipalEventView(
            observation,
            "login-backed rejected start built canonical rejected-start event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 0), observation),
                "canonical rejected start observation did not build");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
            Obelisk::Core::PlayerPrincipalAction::None,
            2,
            "canonical rejected start event view mismatch");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "session end observation did not build");
        RequirePlayerPrincipalEventView(
            observation,
            Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
            Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
            0,
            "session end event view mismatch");
    }

    void TestPlayerPrincipalEventViewRejectsMalformedObservations()
    {
        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
        Require(!Observer::TryMapPlayerPrincipalEventKind(
                    static_cast<Observer::LifecycleRole>(99),
                    kind),
                "unknown lifecycle role mapped to event kind");

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::None;
        Require(!Observer::TryMapPlayerPrincipalAction(
                    static_cast<Observer::PrincipalAction>(99),
                    action),
                "unknown principal action mapped to core action");

        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
        Obelisk::Core::PlayerPrincipalEventView event;
        Observer::CopiedLifecycleObservation observation;
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "valid accepted start observation did not build");

        Observer::CopiedLifecycleObservation malformed = observation;
        malformed.Role = static_cast<Observer::LifecycleRole>(99);
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "unknown lifecycle role built event view");

        malformed = observation;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "accepted start without candidate-created action built event view");

        malformed = observation;
        malformed.BoolCount = 0;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start without canonical bools built event view");

        malformed = observation;
        std::swap(malformed.BoolStorage[0], malformed.BoolStorage[1]);
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with swapped bool fields built event view");

        malformed = observation;
        malformed.Role = Observer::LifecycleRole::SessionStartRejected;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "accepted start bools built rejected event view");

        malformed = observation;
        malformed.BoolStorage[1].Value = false;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "rejected start bools built accepted event view");

        Require(!Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 0), observation),
                "login-backed HandleNewPlayer 1,0 built rejected-start observation");
        malformed = observation;
        malformed.BoolStorage[0].Value = false;
        malformed.BoolStorage[1].Value = true;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "superseded HandleNewPlayer 0,1 tuple built rejected event view");
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "superseded HandleNewPlayer 0,1 tuple built approved event view");
        Require(Observer::TryBuildCopiedLifecycleObservation(HandleNewPlayerInvocation(1, 1), observation),
                "valid accepted start observation did not rebuild after superseded tuple checks");

        malformed = observation;
        malformed.RedactedCount = 2;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with missing redacted field built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[0] = 0;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with zero private subject token built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[0] = std::numeric_limits<uint64_t>::max();
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with validate-only private subject token sentinel built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[1] = 2;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with PlayerData private subject token built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[2] = 3;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "start with PlayerCharacter private subject token built event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(CheckJoinInProgressInvocation(1, 0),
                                                             observation),
                "valid CheckJoinInProgress rejected observation did not build");
        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[0] = 4;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "CheckJoinInProgress rejected observation with private token built event view");
        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[1] = 4;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "CheckJoinInProgress rejected observation with unused private token built event view");
        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[2] = 5;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "CheckJoinInProgress rejected observation with second unused private token built event view");

        Require(Observer::TryBuildCopiedLifecycleDiagnosticObservation(CheckJoinInProgressInvocation(0, 0),
                                                                       observation),
                "CheckJoinInProgress 0,0 diagnostic observation did not build");
        RequireNoPlayerPrincipalEventView(
            observation,
            "CheckJoinInProgress 0,0 diagnostic built event-view evidence");
        malformed = observation;
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "CheckJoinInProgress 0,0 diagnostic built approved event view");

        Require(Observer::TryBuildCopiedLifecycleObservation(OnLogoutInvocation(), observation),
                "valid session end observation did not build");
        malformed = observation;
        malformed.BoolStorage[0] = {
            .Field = LifecycleField::ReturnValue,
            .Value = true,
        };
        malformed.BoolCount = 1;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with bool payload built event view");

        malformed = observation;
        malformed.Action = Observer::PrincipalAction::None;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end without invalidation action built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[0] = 0;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with zero private subject token built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[0] = std::numeric_limits<uint64_t>::max();
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with validate-only private subject token sentinel built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[1] = 6;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with unused private subject token built event view");

        malformed = observation;
        malformed.RedactedProcessLocalSubjectTokens[2] = 7;
        Require(!Observer::TryBuildPlayerPrincipalEventView(malformed, boolStorage, event),
                "session end with second unused private subject token built event view");
    }
}

int main()
{
    TestGateMatrix();
    TestNameAndBudgetPrefilters();
    TestTryIdentifyFastPathsDoNotRead();
    TestFunctionFNameNearMissDiagnosticRemainsNonEvidence();
    TestDispatchGateOnlyCannotBuildLifecycleEvent();
    TestBuildsHandleNewPlayerObservation();
    TestAcceptedObserverTripletsStaySeparateFromDiagnosticCandidates();
    TestBuildsCheckJoinInProgressDiagnosticOnlyObservation();
    TestBuildsK2PostLoginDiagnosticOnlyObservation();
    TestDiagnosticOnlyMatchedAttemptsNeverBuildLifecycleEventAfterOriginal();
    TestOrganicJoinDiagnosticCandidatesRemainNonDispatchable();
    TestCheckJoinInProgressRejectedPathIsReachableThroughObserver();
    TestHandleNewPlayerOneZeroRejectedThroughObserverWithoutBudget();
    TestCheckJoinInProgressRejectedPathIgnoresRedactedObjectPointer();
    TestRejectsInferredCheckJoinInProgressDrift();
    TestAcceptsObservedCheckJoinInProgressDrift();
    TestAcceptsLiveObservedCheckJoinInProgressDrift();
    TestRejectsMixedCurrentRuntimeCheckJoinInProgressDrift();
    TestRejectsCurrentRagnarokCheckJoinInProgressName28514Drift();
    TestCheckJoinInProgressRejectedLogFieldsStayAnalyzerSafe();
    TestBuildsOnLogoutObservationWithoutIdentity();
    TestRedactedObjectFieldsCarryPrivateSubjectTokenWithoutRange();
    TestAcceptsLifecyclePropertyFNameDriftWithRequiredShape();
    TestRejectsPostRestartRagnarokHandleNewPlayerName28419Drift();
    TestCurrentRuntimeAnchorFNameDriftUsesSourceBoundShapeAndK2StaysRejectOnly();
    TestCopiedEventsPreserveOnlyCanonicalBoolPayloads();
    TestObservedFNameDriftCanBuildPostOriginalCopiedEventViews();
    TestDiagnosticBudgetAndExactShapeDriftDoNotHideAcceptedEventTriplets();
    TestRejectedAcceptedTargetsCannotExhaustFixedTripletBudget();
    TestMalformedObservedFNameDriftCannotBuildPostOriginalCopiedEvents();
    TestAcceptedTargetMismatchesRemainNonEvidenceUntilObserverEventBuilds();
    TestRejectsMalformedLifecyclePropertyFNameDriftObservations();
    TestAfterOriginalGuard();
    TestMatchedAttemptRequiresSuccessfulReflectionResult();
    TestNonMatchedShapeOkAttemptsDoNotBuildLifecycleEvent();
    TestDispatchLimitZeroBlocksDispatchBudgetEvenWithShapeOk();
    TestApprovedRuntimeEvidenceLogBudgetKeepsOnlyStrictTripletRoles();
    TestApprovedRuntimeEvidenceLogBudgetDoesNotInferRejectedRoleFromStartAndEnd();
    TestApprovedRuntimeEvidenceLogBudgetWaitsForFinalTokenAssignment();
    TestApprovedRuntimeEvidenceLogBudgetDoesNotStarveLifecycleState();
    TestDiagnosticBudgetExhaustionCannotStarveAcceptedLifecycleBudget();
    TestBudgetRaceDoesNotReadLifecycleParamPayloads();
    TestMissingSubjectTokenRejectsWithoutBudgetOrCopiedObservation();
    TestBuildsPlayerPrincipalEventViews();
    TestPlayerPrincipalEventViewRejectsMalformedObservations();

    std::cout << "ProcessEventPlayerPrincipalLifecycleObserverTests passed\n";
    return 0;
}
