#include "ProcessEventPlayerPrincipalLifecycleObserver.h"

#include <array>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleObserver
{
    namespace
    {
        constexpr int32_t kCheckJoinInProgressNameIndex = 1845;
        constexpr int32_t kHandleNewPlayerNameIndex = 2170;
        constexpr int32_t kOnLogoutNameIndex = 2384;
        constexpr int32_t kGameModeK2PostLoginNameIndex = 4943;
        constexpr int32_t kOnPostLoginDelegateNameIndex = 28545;
        constexpr int32_t kOnStartNewPlayerDelegateNameIndex = 28555;
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
        constexpr int32_t kObservedHandleNewPlayerName0 = 28418;
        constexpr int32_t kObservedHandleNewPlayerName1 = 21314;
        constexpr int32_t kObservedHandleNewPlayerName2 = 22968;
        constexpr int32_t kObservedHandleNewPlayerName3 = 28516;
        constexpr int32_t kObservedHandleNewPlayerName4 = 17724;
        constexpr int32_t kObservedHandleNewPlayerPostRestartName0 = 28417;
        constexpr int32_t kObservedHandleNewPlayerPostRestartName1 = 21313;
        constexpr int32_t kObservedHandleNewPlayerPostRestartName2 = 22967;
        constexpr int32_t kObservedHandleNewPlayerPostRestartName3 = 28515;
        constexpr int32_t kObservedHandleNewPlayerPostRestartName4 = 17723;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260606Name0 = 28414;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260606Name1 = 21310;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260606Name2 = 22964;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260606Name3 = 28512;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260606Name4 = 17720;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260607Name0 = 28414;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260607Name1 = 21310;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260607Name2 = 22964;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260607Name3 = 28512;
        constexpr int32_t kObservedHandleNewPlayerRagnarokRestart20260607Name4 = 17719;
        constexpr int32_t kObservedCheckJoinInProgressRagnarokRestart20260607Name0 = 28512;
        constexpr int32_t kObservedCheckJoinInProgressRagnarokRestart20260607Name1 = 28414;
        constexpr int32_t kObservedCheckJoinInProgressRagnarokRestart20260607Name2 = 17719;
        constexpr int32_t kObservedCheckJoinInProgressRagnarokLive20260607Name2 = 17720;
        constexpr int32_t kObservedCheckJoinInProgressTheIsland20260607Name0 = 28520;
        constexpr int32_t kObservedCheckJoinInProgressTheIsland20260607Name1 = 28422;
        constexpr int32_t kObservedCheckJoinInProgressTheIsland20260607Name2 = 17729;
        constexpr int32_t kObservedOnLogoutName0 = 28550;
        constexpr int32_t kObservedOnLogoutPostRestartName0 = 28549;
        constexpr int32_t kObservedOnLogoutRagnarokRestart20260606Name0 = 28546;
        constexpr int32_t kObservedOnLogoutCurrentRuntime20260607Name0 = 28554;
        constexpr int32_t kObservedHandleNewPlayerCurrentRuntime20260607Name0 = 28422;
        constexpr int32_t kObservedHandleNewPlayerCurrentRuntime20260607Name1 = 21318;
        constexpr int32_t kObservedHandleNewPlayerCurrentRuntime20260607Name2 = 22972;
        constexpr int32_t kObservedHandleNewPlayerCurrentRuntime20260607Name3 = 28520;
        constexpr int32_t kObservedHandleNewPlayerCurrentRuntime20260607Name4 = 17727;
        constexpr std::array<std::array<int32_t, 5>, 5> kObservedHandleNewPlayerDriftChains{{
            {kObservedHandleNewPlayerName0,
             kObservedHandleNewPlayerName1,
             kObservedHandleNewPlayerName2,
             kObservedHandleNewPlayerName3,
             kObservedHandleNewPlayerName4},
            {kObservedHandleNewPlayerPostRestartName0,
             kObservedHandleNewPlayerPostRestartName1,
             kObservedHandleNewPlayerPostRestartName2,
             kObservedHandleNewPlayerPostRestartName3,
             kObservedHandleNewPlayerPostRestartName4},
            {kObservedHandleNewPlayerRagnarokRestart20260606Name0,
             kObservedHandleNewPlayerRagnarokRestart20260606Name1,
             kObservedHandleNewPlayerRagnarokRestart20260606Name2,
             kObservedHandleNewPlayerRagnarokRestart20260606Name3,
             kObservedHandleNewPlayerRagnarokRestart20260606Name4},
            {kObservedHandleNewPlayerRagnarokRestart20260607Name0,
             kObservedHandleNewPlayerRagnarokRestart20260607Name1,
             kObservedHandleNewPlayerRagnarokRestart20260607Name2,
             kObservedHandleNewPlayerRagnarokRestart20260607Name3,
             kObservedHandleNewPlayerRagnarokRestart20260607Name4},
            {kObservedHandleNewPlayerCurrentRuntime20260607Name0,
             kObservedHandleNewPlayerCurrentRuntime20260607Name1,
             kObservedHandleNewPlayerCurrentRuntime20260607Name2,
             kObservedHandleNewPlayerCurrentRuntime20260607Name3,
             kObservedHandleNewPlayerCurrentRuntime20260607Name4},
        }};
        constexpr std::array<std::array<int32_t, 3>, 3> kObservedCheckJoinInProgressDriftChains{{
            {kObservedCheckJoinInProgressRagnarokRestart20260607Name0,
             kObservedCheckJoinInProgressRagnarokRestart20260607Name1,
             kObservedCheckJoinInProgressRagnarokRestart20260607Name2},
            {kObservedCheckJoinInProgressRagnarokRestart20260607Name0,
             kObservedCheckJoinInProgressRagnarokRestart20260607Name1,
             kObservedCheckJoinInProgressRagnarokLive20260607Name2},
            {kObservedCheckJoinInProgressTheIsland20260607Name0,
             kObservedCheckJoinInProgressTheIsland20260607Name1,
             kObservedCheckJoinInProgressTheIsland20260607Name2},
        }};
        constexpr uint64_t kMaxLogLimit = 10;
        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
        constexpr uint32_t kK2PostLoginFunctionFlags = 0x0c020800;
        constexpr uint32_t kCheckJoinInProgressFunctionFlags = 0x0c080c00;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr size_t kBoolPropertyFieldSizeOffset = 0x70;
        constexpr size_t kBoolPropertyByteOffsetOffset = 0x71;
        constexpr size_t kBoolPropertyByteMaskOffset = 0x72;
        constexpr size_t kBoolPropertyFieldMaskOffset = 0x73;
        constexpr uint8_t kBoolFieldSize = 0x01;
        constexpr uint8_t kBoolByteOffset = 0x00;
        constexpr uint8_t kBoolByteMask = 0x01;
        constexpr uint8_t kBoolFieldMask = 0xff;

        struct LifecycleFieldShape
        {
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField Field =
                Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer;
            int32_t NameIndex = -1;
            int32_t Offset = -1;
            size_t Size = 0;
            bool ExposesRange = false;
            bool Redacted = true;
        };

        struct NearMissFieldSpec
        {
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField Field =
                Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer;
            int32_t NameIndex = -1;
            int32_t Offset = -1;
            size_t Size = 0;
            int32_t ClassNameIndex = -1;
            int32_t ClassObjectIndex = -1;
            uint64_t PropertyFlags = 0;
        };

        struct NearMissFunctionSpec
        {
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction Function =
                Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer;
            int32_t NameIndex = -1;
            int32_t OuterNameIndex = -1;
            int32_t OuterObjectIndex = -1;
            uint32_t FunctionFlags = 0;
            uint16_t NumParms = 0;
            uint16_t ParmsSize = 0;
            uint16_t ReturnValueOffset = 0xffff;
            const NearMissFieldSpec* Fields = nullptr;
            size_t FieldCount = 0;
        };

        constexpr std::array<NearMissFieldSpec, 3> kNearMissCheckJoinInProgressFields{{
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
             kBIsFromLoginNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
             kReturnValueNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags},
        }};

        constexpr std::array<NearMissFieldSpec, 5> kNearMissHandleNewPlayerFields{{
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::PlayerData,
             kPlayerDataNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::PlayerCharacter,
             kPlayerCharacterNameIndex,
             0x10,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin,
             kBIsFromLoginNameIndex,
             0x18,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags},
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::ReturnValue,
             kReturnValueNameIndex,
             0x19,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags},
        }};

        constexpr std::array<NearMissFieldSpec, 1> kNearMissK2PostLoginFields{{
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
        }};

        constexpr std::array<NearMissFieldSpec, 1> kNearMissOnLogoutFields{{
            {Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::Exiting,
             kExitingNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags},
        }};

        constexpr NearMissFunctionSpec kNearMissCheckJoinInProgressSpec{
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::CheckJoinInProgressDiagnostic,
            kCheckJoinInProgressNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kCheckJoinInProgressFunctionFlags,
            3,
            0x11,
            0x10,
            kNearMissCheckJoinInProgressFields.data(),
            kNearMissCheckJoinInProgressFields.size(),
        };

        constexpr NearMissFunctionSpec kNearMissHandleNewPlayerSpec{
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer,
            kHandleNewPlayerNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            5,
            0x1a,
            0x19,
            kNearMissHandleNewPlayerFields.data(),
            kNearMissHandleNewPlayerFields.size(),
        };

        constexpr NearMissFunctionSpec kNearMissK2PostLoginSpec{
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::K2PostLoginDiagnostic,
            kGameModeK2PostLoginNameIndex,
            kGameModeNameIndex,
            kGameModeObjectIndex,
            kK2PostLoginFunctionFlags,
            1,
            0x08,
            0xffff,
            kNearMissK2PostLoginFields.data(),
            kNearMissK2PostLoginFields.size(),
        };

        constexpr NearMissFunctionSpec kNearMissOnLogoutSpec{
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::OnLogout,
            kOnLogoutNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            1,
            0x08,
            0xffff,
            kNearMissOnLogoutFields.data(),
            kNearMissOnLogoutFields.size(),
        };

        bool ParseUnsigned(const char* text, uint64_t& out)
        {
            if (!text || text[0] == '\0')
                return false;
            for (const char* cursor = text; *cursor; ++cursor)
            {
                if (*cursor < '0' || *cursor > '9')
                    return false;
            }

            errno = 0;
            char* end = nullptr;
            const unsigned long long parsed = std::strtoull(text, &end, 10);
            if (errno == ERANGE || !end || *end != '\0' ||
                parsed > std::numeric_limits<uint64_t>::max())
            {
                return false;
            }
            out = static_cast<uint64_t>(parsed);
            return true;
        }

        bool TryCopyBool(const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field,
                         LifecycleBoolObservation& out)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            switch (field.Field)
            {
            case LifecycleField::BIsFromLogin:
            case LifecycleField::ReturnValue:
                break;
            case LifecycleField::NewPlayer:
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::Exiting:
                return false;
            }

            if (!field.ExposesRange ||
                field.Redacted ||
                !field.HasCopiedBoolValue ||
                field.CopiedBoolValue > 1 ||
                field.Range.Data != nullptr ||
                field.Range.Size != 0 ||
                field.Size != sizeof(uint8_t))
            {
                return false;
            }

            out.Field = field.Field;
            out.Value = field.CopiedBoolValue != 0;
            return true;
        }

        bool AddRedactedField(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field,
                              uint64_t processLocalSubjectToken,
                              CopiedLifecycleObservation& out)
        {
            if (out.RedactedCount >= out.RedactedStorage.size())
                return false;
            out.RedactedStorage[out.RedactedCount] = field;
            out.RedactedProcessLocalSubjectTokens[out.RedactedCount] = processLocalSubjectToken;
            ++out.RedactedCount;
            return true;
        }

        bool IsAssignedProcessLocalSubjectToken(uint64_t token)
        {
            return token != 0 && token != std::numeric_limits<uint64_t>::max();
        }

        uint64_t CopyableProcessLocalSubjectToken(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            switch (field.Field)
            {
            case LifecycleField::NewPlayer:
            case LifecycleField::Exiting:
                return IsAssignedProcessLocalSubjectToken(field.ProcessLocalSubjectToken)
                    ? field.ProcessLocalSubjectToken
                    : 0;
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::BIsFromLogin:
            case LifecycleField::ReturnValue:
                return 0;
            }
            return 0;
        }

        bool AddBoolField(const LifecycleBoolObservation& value, CopiedLifecycleObservation& out)
        {
            if (out.BoolCount >= out.BoolStorage.size())
                return false;
            out.BoolStorage[out.BoolCount++] = value;
            return true;
        }

        bool RedactedFieldHasNoCopiedPayload(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange& field)
        {
            return field.Range.Data == nullptr &&
                field.Range.Size == 0 &&
                !field.HasCopiedBoolValue &&
                field.CopiedBoolValue == 0;
        }

        bool TryMapPlayerPrincipalBoolField(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field,
            Obelisk::Core::PlayerPrincipalBoolField& out)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            switch (field)
            {
            case LifecycleField::BIsFromLogin:
                out = Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin;
                return true;
            case LifecycleField::ReturnValue:
                out = Obelisk::Core::PlayerPrincipalBoolField::ReturnValue;
                return true;
            case LifecycleField::NewPlayer:
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::Exiting:
                return false;
            }
            return false;
        }

        bool HasCanonicalHandleNewPlayerRedactedSubjectShape(const CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 3 &&
                observation.RedactedStorage[0] == LifecycleField::NewPlayer &&
                observation.RedactedStorage[1] == LifecycleField::PlayerData &&
                observation.RedactedStorage[2] == LifecycleField::PlayerCharacter &&
                observation.RedactedProcessLocalSubjectTokens[0] != 0 &&
                observation.RedactedProcessLocalSubjectTokens[0] != std::numeric_limits<uint64_t>::max() &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        bool HasCanonicalOnLogoutRedactedSubjectShape(const CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 1 &&
                observation.RedactedStorage[0] == LifecycleField::Exiting &&
                observation.RedactedProcessLocalSubjectTokens[0] != 0 &&
                observation.RedactedProcessLocalSubjectTokens[0] != std::numeric_limits<uint64_t>::max() &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        bool HasCanonicalCheckJoinRejectedRedactedShape(const CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 1 &&
                observation.RedactedStorage[0] == LifecycleField::NewPlayer &&
                observation.RedactedProcessLocalSubjectTokens[0] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        void ReplaceValidateOnlySubjectTokenSentinelForCopiedValidation(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            constexpr uint64_t kValidationOnlySentinel = std::numeric_limits<uint64_t>::max();

            for (auto& field : invocation.Fields)
            {
                switch (field.Field)
                {
                case LifecycleField::NewPlayer:
                case LifecycleField::Exiting:
                    if (field.ProcessLocalSubjectToken == kValidationOnlySentinel)
                        field.ProcessLocalSubjectToken = 1;
                    break;
                case LifecycleField::PlayerData:
                case LifecycleField::PlayerCharacter:
                case LifecycleField::BIsFromLogin:
                case LifecycleField::ReturnValue:
                    break;
                }
            }
        }

        bool TryGetExpectedFieldShape(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function,
            size_t position,
            LifecycleFieldShape& out)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

            switch (function)
            {
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
                switch (position)
                {
                case 0:
                    out = {LifecycleField::BIsFromLogin,
                           kBIsFromLoginNameIndex,
                           0x00,
                           kBoolPropertySize,
                           true,
                           false};
                    return true;
                case 1:
                    out = {LifecycleField::NewPlayer,
                           kNewPlayerNameIndex,
                           0x08,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                case 2:
                    out = {LifecycleField::ReturnValue,
                           kReturnValueNameIndex,
                           0x10,
                           kBoolPropertySize,
                           true,
                           false};
                    return true;
                default:
                    return false;
                }
            case LifecycleFunction::K2PostLoginDiagnostic:
                if (position == 0)
                {
                    out = {LifecycleField::NewPlayer,
                           kNewPlayerNameIndex,
                           0x00,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                }
                return false;
            case LifecycleFunction::HandleNewPlayer:
                switch (position)
                {
                case 0:
                    out = {LifecycleField::NewPlayer,
                           kNewPlayerNameIndex,
                           0x00,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                case 1:
                    out = {LifecycleField::PlayerData,
                           kPlayerDataNameIndex,
                           0x08,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                case 2:
                    out = {LifecycleField::PlayerCharacter,
                           kPlayerCharacterNameIndex,
                           0x10,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                case 3:
                    out = {LifecycleField::BIsFromLogin,
                           kBIsFromLoginNameIndex,
                           0x18,
                           kBoolPropertySize,
                           true,
                           false};
                    return true;
                case 4:
                    out = {LifecycleField::ReturnValue,
                           kReturnValueNameIndex,
                           0x19,
                           kBoolPropertySize,
                           true,
                           false};
                    return true;
                default:
                    return false;
                }
            case LifecycleFunction::OnLogout:
                if (position == 0)
                {
                    out = {LifecycleField::Exiting,
                           kExitingNameIndex,
                           0x00,
                           kObjectPropertySize,
                           false,
                           true};
                    return true;
                }
                return false;
            }
            return false;
        }

        bool AllowsLifecyclePropertyFNameDrift(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
            switch (function)
            {
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
            case LifecycleFunction::HandleNewPlayer:
            case LifecycleFunction::OnLogout:
                return true;
            case LifecycleFunction::K2PostLoginDiagnostic:
                return false;
            }
            return false;
        }

        bool MatchesDifferentExpectedFieldName(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function,
            size_t position,
            int32_t observedNameIndex)
        {
            for (size_t index = 0;; ++index)
            {
                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(function, index, expected))
                    return false;
                if (index != position && expected.NameIndex == observedNameIndex)
                    return true;
            }
        }

        bool IsApprovedObservedPropertyFNameDrift(
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function,
            size_t position,
            int32_t observedNameIndex)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

            switch (function)
            {
            case LifecycleFunction::HandleNewPlayer:
                for (const auto& chain : kObservedHandleNewPlayerDriftChains)
                {
                    if (position < chain.size() && chain[position] == observedNameIndex)
                        return true;
                }
                return false;
            case LifecycleFunction::OnLogout:
                return position == 0 &&
                    (observedNameIndex == kObservedOnLogoutName0 ||
                     observedNameIndex == kObservedOnLogoutPostRestartName0 ||
                     observedNameIndex == kObservedOnLogoutRagnarokRestart20260606Name0 ||
                     observedNameIndex == kObservedOnLogoutCurrentRuntime20260607Name0);
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
                for (const auto& chain : kObservedCheckJoinInProgressDriftChains)
                {
                    if (position < chain.size() && chain[position] == observedNameIndex)
                        return true;
                }
                return false;
            case LifecycleFunction::K2PostLoginDiagnostic:
                return false;
            }
            return false;
        }

        bool MatchesApprovedObservedPropertyFNameDriftChain(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

            switch (invocation.Function)
            {
            case LifecycleFunction::HandleNewPlayer:
                if (invocation.Fields.size() != kObservedHandleNewPlayerDriftChains[0].size())
                    return false;
                for (const auto& chain : kObservedHandleNewPlayerDriftChains)
                {
                    bool matches = true;
                    for (size_t index = 0; index < chain.size(); ++index)
                    {
                        if (invocation.Fields[index].PropertyNameIndex != chain[index])
                        {
                            matches = false;
                            break;
                        }
                    }
                    if (matches)
                        return true;
                }
                return false;
            case LifecycleFunction::OnLogout:
                return invocation.Fields.size() == 1 &&
                    (invocation.Fields[0].PropertyNameIndex == kObservedOnLogoutName0 ||
                     invocation.Fields[0].PropertyNameIndex == kObservedOnLogoutPostRestartName0 ||
                     invocation.Fields[0].PropertyNameIndex ==
                         kObservedOnLogoutRagnarokRestart20260606Name0 ||
                     invocation.Fields[0].PropertyNameIndex ==
                         kObservedOnLogoutCurrentRuntime20260607Name0);
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
                if (invocation.Fields.size() != kObservedCheckJoinInProgressDriftChains[0].size())
                    return false;
                for (const auto& chain : kObservedCheckJoinInProgressDriftChains)
                {
                    bool matches = true;
                    for (size_t index = 0; index < chain.size(); ++index)
                    {
                        if (invocation.Fields[index].PropertyNameIndex != chain[index])
                        {
                            matches = false;
                            break;
                        }
                    }
                    if (matches)
                        return true;
                }
                return false;
            case LifecycleFunction::K2PostLoginDiagnostic:
                return false;
            }
            return false;
        }

        bool HasExpectedLifecycleFieldShape(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation)
        {
            for (size_t index = 0; index < invocation.Fields.size(); ++index)
            {
                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(invocation.Function, index, expected))
                    return false;

                const auto& field = invocation.Fields[index];
                if (field.Field != expected.Field ||
                    field.Offset != expected.Offset ||
                    field.Size != expected.Size ||
                    field.ExposesRange != expected.ExposesRange ||
                    field.Redacted != expected.Redacted)
                {
                    return false;
                }
            }

            LifecycleFieldShape ignored;
            return !TryGetExpectedFieldShape(invocation.Function, invocation.Fields.size(), ignored);
        }

        bool HasExpectedLifecyclePropertyNames(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation)
        {
            if (invocation.PropertyNameIndicesMatched)
            {
                if (!invocation.PropertyFNameDrifts.empty())
                    return false;
                for (size_t index = 0; index < invocation.Fields.size(); ++index)
                {
                    LifecycleFieldShape expected;
                    if (!TryGetExpectedFieldShape(invocation.Function, index, expected) ||
                        invocation.Fields[index].PropertyNameIndex != expected.NameIndex)
                    {
                        return false;
                    }
                }
                return true;
            }

            if (!AllowsLifecyclePropertyFNameDrift(invocation.Function) ||
                invocation.PropertyFNameDrifts.empty() ||
                invocation.PropertyFNameDrifts.size() != invocation.Fields.size())
            {
                return false;
            }

            std::array<bool, 5> driftByPosition{};
            for (const auto& drift : invocation.PropertyFNameDrifts)
            {
                if (drift.Position >= invocation.Fields.size() ||
                    drift.Position >= driftByPosition.size())
                    return false;

                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(invocation.Function, drift.Position, expected))
                    return false;

                if (driftByPosition[drift.Position])
                    return false;

                const auto& field = invocation.Fields[drift.Position];
                if (drift.Field != expected.Field ||
                    field.Field != expected.Field ||
                    drift.ExpectedNameIndex != expected.NameIndex ||
                    !IsApprovedObservedPropertyFNameDrift(invocation.Function,
                                                          drift.Position,
                                                          drift.ObservedNameIndex) ||
                    drift.ObservedNameIndex == expected.NameIndex ||
                    MatchesDifferentExpectedFieldName(invocation.Function,
                                                      drift.Position,
                                                      drift.ObservedNameIndex) ||
                    field.PropertyNameIndex != drift.ObservedNameIndex)
                {
                    return false;
                }

                driftByPosition[drift.Position] = true;
            }

            if (!MatchesApprovedObservedPropertyFNameDriftChain(invocation))
                return false;

            for (size_t index = 0; index < invocation.Fields.size(); ++index)
            {
                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(invocation.Function, index, expected))
                    return false;

                const bool fieldNameDrifted = invocation.Fields[index].PropertyNameIndex != expected.NameIndex;
                if (fieldNameDrifted != driftByPosition[index])
                    return false;
            }

            return true;
        }

        bool HasRequiredLifecycleShapeAndPropertyNames(
            const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation)
        {
            return HasExpectedLifecycleFieldShape(invocation) &&
                HasExpectedLifecyclePropertyNames(invocation);
        }

        bool ReadNearMissByteAt(const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                const void* base,
                                size_t offset,
                                uint8_t& out)
        {
            out = 0;
            if (!base)
                return false;
            const auto* address = reinterpret_cast<const uint8_t*>(base) + offset;
            if (!reader.CanRead(address, sizeof(uint8_t)))
                return false;
            std::memcpy(&out, address, sizeof(uint8_t));
            return true;
        }

        bool NearMissBoolPropertyMetadataMatches(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::UPropertyView& property)
        {
            uint8_t fieldSize = 0;
            uint8_t byteOffset = 0;
            uint8_t byteMask = 0;
            uint8_t fieldMask = 0;
            return ReadNearMissByteAt(reader, property.Address, kBoolPropertyFieldSizeOffset, fieldSize) &&
                ReadNearMissByteAt(reader, property.Address, kBoolPropertyByteOffsetOffset, byteOffset) &&
                ReadNearMissByteAt(reader, property.Address, kBoolPropertyByteMaskOffset, byteMask) &&
                ReadNearMissByteAt(reader, property.Address, kBoolPropertyFieldMaskOffset, fieldMask) &&
                fieldSize == kBoolFieldSize &&
                byteOffset == kBoolByteOffset &&
                byteMask == kBoolByteMask &&
                fieldMask == kBoolFieldMask;
        }

        bool NearMissClassMatches(const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
                                  const void* klass,
                                  int32_t expectedNameIndex,
                                  int32_t expectedObjectIndex)
        {
            Obelisk::UE::RuntimeReflection::UObjectView value;
            if (!klass ||
                !Obelisk::UE::RuntimeReflection::TryReadUObject(reader, layout, klass, value))
            {
                return false;
            }
            return value.NamePrivate.ComparisonIndex == expectedNameIndex &&
                value.NamePrivate.Number == 0 &&
                value.InternalIndex == expectedObjectIndex;
        }

        bool NearMissOuterMatches(const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
                                  const void* outer,
                                  int32_t expectedNameIndex,
                                  int32_t expectedObjectIndex)
        {
            Obelisk::UE::RuntimeReflection::UObjectView value;
            if (!outer ||
                !Obelisk::UE::RuntimeReflection::TryReadUObject(reader, layout, outer, value))
            {
                return false;
            }
            return value.NamePrivate.ComparisonIndex == expectedNameIndex &&
                value.NamePrivate.Number == 0 &&
                value.InternalIndex == expectedObjectIndex;
        }

        bool NearMissPropertyShapeMatches(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UPropertyView& property,
            const NearMissFieldSpec& spec)
        {
            if (property.Object.NamePrivate.Number != 0 ||
                property.OffsetInternal != spec.Offset ||
                property.ByteSize != spec.Size ||
                property.ElementSize != static_cast<int32_t>(spec.Size) ||
                property.ArrayDim != 1 ||
                property.PropertyFlags != spec.PropertyFlags ||
                !NearMissClassMatches(reader,
                                      layout,
                                      property.Object.ClassPrivate,
                                      spec.ClassNameIndex,
                                      spec.ClassObjectIndex))
            {
                return false;
            }
            if (spec.ClassNameIndex == kBoolPropertyClassNameIndex &&
                !NearMissBoolPropertyMetadataMatches(reader, property))
            {
                return false;
            }
            return true;
        }

        bool NearMissLifecycleFunctionShapeMatches(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function,
            const NearMissFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.Number != 0 ||
                function.FunctionFlags != spec.FunctionFlags ||
                function.NumParms != spec.NumParms ||
                function.ParmsSize != spec.ParmsSize ||
                function.ReturnValueOffset != spec.ReturnValueOffset ||
                function.Parameters.size() != spec.FieldCount ||
                !NearMissClassMatches(reader,
                                      layout,
                                      function.Object.ClassPrivate,
                                      kFunctionClassNameIndex,
                                      kFunctionClassObjectIndex) ||
                !NearMissOuterMatches(reader,
                                      layout,
                                      function.Object.OuterPrivate,
                                      spec.OuterNameIndex,
                                      spec.OuterObjectIndex))
            {
                return false;
            }

            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            invocation.Function = spec.Function;
            invocation.FunctionNameIndex = spec.NameIndex;
            invocation.OuterNameIndex = spec.OuterNameIndex;
            invocation.HasParameterRanges = false;
            invocation.PropertyNameIndicesMatched = true;
            invocation.Fields.reserve(spec.FieldCount);
            invocation.PropertyFNameDrifts.reserve(spec.FieldCount);

            for (size_t index = 0; index < spec.FieldCount; ++index)
            {
                const auto& property = function.Parameters[index];
                const NearMissFieldSpec& fieldSpec = spec.Fields[index];
                if (!NearMissPropertyShapeMatches(reader, layout, property, fieldSpec))
                    return false;

                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(spec.Function, index, expected))
                    return false;

                Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange field;
                field.Field = expected.Field;
                field.PropertyNameIndex = property.Object.NamePrivate.ComparisonIndex;
                field.Offset = expected.Offset;
                field.Size = expected.Size;
                field.ExposesRange = expected.ExposesRange;
                field.Redacted = expected.Redacted;
                invocation.Fields.push_back(field);

                if (property.Object.NamePrivate.ComparisonIndex != fieldSpec.NameIndex)
                {
                    invocation.PropertyNameIndicesMatched = false;
                    invocation.PropertyFNameDriftDiagnosticOnly = true;
                    invocation.PropertyFNameDrifts.push_back({
                        index,
                        fieldSpec.Field,
                        fieldSpec.NameIndex,
                        property.Object.NamePrivate.ComparisonIndex,
                    });
                }
            }

            return HasExpectedLifecyclePropertyNames(invocation);
        }

        void AppendNearMissKeyValueSigned(std::string& reason, std::string_view key, int64_t value)
        {
            reason += "_";
            reason += key;
            reason += "_";
            reason += std::to_string(value);
        }

        void AppendNearMissExpectedPropertyNameIndexChain(std::string& reason,
                                                          const NearMissFunctionSpec& spec)
        {
            reason += "_expected_property_name_indices";
            for (size_t index = 0; index < spec.FieldCount; ++index)
            {
                reason += index == 0 ? "_" : ".";
                reason += std::to_string(spec.Fields[index].NameIndex);
            }
        }

        void AppendNearMissObservedPropertyNameIndexChain(
            std::string& reason,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function)
        {
            reason += "_observed_property_name_indices";
            for (size_t index = 0; index < function.Parameters.size(); ++index)
            {
                reason += index == 0 ? "_" : ".";
                reason += std::to_string(function.Parameters[index].Object.NamePrivate.ComparisonIndex);
            }
        }

        void AppendNearMissDiagnosticNonClaimFields(std::string& reason)
        {
            reason += "_metadata_only_true";
            reason += "_identity_logged_false";
            reason += "_evidence_claim_none";
            reason += "_principal_claim_none";
        }

        void AppendNearMissPropertyNameIndexChains(
            std::string& reason,
            const NearMissFunctionSpec& spec,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function)
        {
            AppendNearMissExpectedPropertyNameIndexChain(reason, spec);
            AppendNearMissObservedPropertyNameIndexChain(reason, function);
        }

        void AppendNearMissObservedOuter(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function,
            std::string& reason)
        {
            Obelisk::UE::RuntimeReflection::UObjectView outer;
            if (function.Object.OuterPrivate &&
                Obelisk::UE::RuntimeReflection::TryReadUObject(
                    reader,
                    layout,
                    function.Object.OuterPrivate,
                    outer))
            {
                AppendNearMissKeyValueSigned(reason,
                                             "observed_outer_name_index",
                                             outer.NamePrivate.ComparisonIndex);
                return;
            }

            reason += "_observed_outer_unreadable";
        }

        std::string BuildFunctionFNameNearMissReason(const NearMissFunctionSpec& spec,
                                                     int32_t observedNameIndex)
        {
            std::string reason = "lifecycle_function_FName_near_miss";
            reason += "_expected_name_index_";
            reason += std::to_string(spec.NameIndex);
            reason += "_observed_name_index_";
            reason += std::to_string(observedNameIndex);
            reason += "_target_";
            reason += LifecycleTargetName(spec.Function);
            AppendNearMissDiagnosticNonClaimFields(reason);
            return reason;
        }

        std::string BuildRejectedFunctionFNameNearMissReason(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function,
            const NearMissFunctionSpec& spec,
            std::string_view cause)
        {
            std::string reason = "lifecycle_function_FName_near_miss_rejected";
            reason += "_cause_";
            reason += cause;
            reason += "_target_";
            reason += LifecycleTargetName(spec.Function);
            AppendNearMissDiagnosticNonClaimFields(reason);
            AppendNearMissPropertyNameIndexChains(reason, spec, function);
            AppendNearMissKeyValueSigned(reason, "expected_name_index", spec.NameIndex);
            AppendNearMissKeyValueSigned(reason,
                                         "observed_name_index",
                                         function.Object.NamePrivate.ComparisonIndex);
            AppendNearMissKeyValueSigned(reason, "expected_outer_name_index", spec.OuterNameIndex);
            AppendNearMissObservedOuter(reader, layout, function, reason);
            return reason;
        }

        const NearMissFunctionSpec* MatchedNearMissLifecycleFunctionSpec(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function)
        {
            const std::array<const NearMissFunctionSpec*, 4> specs{{
                &kNearMissCheckJoinInProgressSpec,
                &kNearMissHandleNewPlayerSpec,
                &kNearMissK2PostLoginSpec,
                &kNearMissOnLogoutSpec,
            }};

            for (const NearMissFunctionSpec* spec : specs)
            {
                if (function.Object.NamePrivate.ComparisonIndex == spec->NameIndex)
                    continue;
                if (NearMissLifecycleFunctionShapeMatches(reader, layout, function, *spec))
                    return spec;
            }
            return nullptr;
        }

        bool NearMissLifecycleFunctionMetadataShapeMatches(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function,
            const NearMissFunctionSpec& spec,
            std::string& reason)
        {
            reason.clear();
            if (function.Object.NamePrivate.ComparisonIndex == spec.NameIndex ||
                function.Object.NamePrivate.Number != 0 ||
                function.FunctionFlags != spec.FunctionFlags ||
                function.NumParms != spec.NumParms ||
                function.ParmsSize != spec.ParmsSize ||
                function.ReturnValueOffset != spec.ReturnValueOffset ||
                function.Parameters.size() != spec.FieldCount ||
                !NearMissClassMatches(reader,
                                      layout,
                                      function.Object.ClassPrivate,
                                      kFunctionClassNameIndex,
                                      kFunctionClassObjectIndex))
            {
                return false;
            }

            const bool outerMatches =
                NearMissOuterMatches(reader,
                                     layout,
                                     function.Object.OuterPrivate,
                                     spec.OuterNameIndex,
                                     spec.OuterObjectIndex);

            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            invocation.Function = spec.Function;
            invocation.FunctionNameIndex = spec.NameIndex;
            invocation.OuterNameIndex = spec.OuterNameIndex;
            invocation.HasParameterRanges = false;
            invocation.PropertyNameIndicesMatched = true;
            invocation.Fields.reserve(spec.FieldCount);
            invocation.PropertyFNameDrifts.reserve(spec.FieldCount);

            for (size_t index = 0; index < spec.FieldCount; ++index)
            {
                const auto& property = function.Parameters[index];
                const NearMissFieldSpec& fieldSpec = spec.Fields[index];
                if (!NearMissPropertyShapeMatches(reader, layout, property, fieldSpec))
                    return false;

                LifecycleFieldShape expected;
                if (!TryGetExpectedFieldShape(spec.Function, index, expected))
                    return false;

                Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFieldRange field;
                field.Field = expected.Field;
                field.PropertyNameIndex = property.Object.NamePrivate.ComparisonIndex;
                field.Offset = expected.Offset;
                field.Size = expected.Size;
                field.ExposesRange = expected.ExposesRange;
                field.Redacted = expected.Redacted;
                invocation.Fields.push_back(field);

                if (property.Object.NamePrivate.ComparisonIndex != fieldSpec.NameIndex)
                {
                    invocation.PropertyNameIndicesMatched = false;
                    invocation.PropertyFNameDriftDiagnosticOnly = true;
                    invocation.PropertyFNameDrifts.push_back({
                        index,
                        fieldSpec.Field,
                        fieldSpec.NameIndex,
                        property.Object.NamePrivate.ComparisonIndex,
                    });
                }
            }

            if (!outerMatches)
            {
                reason = BuildRejectedFunctionFNameNearMissReason(
                    reader,
                    layout,
                    function,
                    spec,
                    "outer_mismatch");
                return true;
            }

            if (HasExpectedLifecyclePropertyNames(invocation))
                return false;

            reason = BuildRejectedFunctionFNameNearMissReason(
                reader,
                layout,
                function,
                spec,
                "property_FName_chain_unapproved");
            return true;
        }

        const NearMissFunctionSpec* MatchedRejectedNearMissLifecycleFunctionSpec(
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            const Obelisk::UE::RuntimeReflection::FieldLayout& layout,
            const Obelisk::UE::RuntimeReflection::UFunctionView& function,
            std::string& reason)
        {
            const std::array<const NearMissFunctionSpec*, 4> specs{{
                &kNearMissCheckJoinInProgressSpec,
                &kNearMissHandleNewPlayerSpec,
                &kNearMissK2PostLoginSpec,
                &kNearMissOnLogoutSpec,
            }};

            for (const NearMissFunctionSpec* spec : specs)
            {
                if (NearMissLifecycleFunctionMetadataShapeMatches(reader, layout, function, *spec, reason))
                    return spec;
            }
            reason.clear();
            return nullptr;
        }

        Attempt TryIdentifyInvocationWithTokenMode(
            const Gate& gate,
            int32_t nameIndex,
            const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
            void* function,
            void* params,
            Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode tokenMode)
        {
            if (!gate.Enabled())
                return {};

            if (!IsReflectedLifecycleNameIndex(nameIndex))
            {
                return {
                    AttemptStatus::NonLifecycleFunction,
                    {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                    {},
                };
            }

            Obelisk::UE::RuntimeReflection::ReadOptions options =
                Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
            Obelisk::UE::RuntimeReflection::ReadResult result;
            try
            {
                result = Obelisk::UE::PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                    reader, options, function, params, invocation, tokenMode);
            }
            catch (...)
            {
                return {
                    AttemptStatus::Rejected,
                    {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                    {},
                };
            }
            if (!result)
                return {AttemptStatus::Rejected, std::move(result), {}};
            if (invocation.FunctionNameIndex != nameIndex)
            {
                return {
                    AttemptStatus::Rejected,
                    Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                        Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                        "player lifecycle prefilter FName does not match reflected UFunction FName"),
                    {},
                };
            }

            return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
        }
    }

    Gate EvaluateGate(const char* enableLifecycleObserver,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256,
                      const char* logLimit,
                      const char* dispatchLimit)
    {
        if (!enableLifecycleObserver || std::strcmp(enableLifecycleObserver, "1") != 0)
            return {};

        if (!observerDebugProfileEnabled)
            return {GateStatus::MissingObserverDebugProfile, {}};
        if (!observerDebugWindowEnabled)
            return {GateStatus::MissingObserverDebugWindow, {}};
        if (!instanceMarkerEnabled)
            return {GateStatus::MissingInstanceMarker, {}};
        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};
        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        if (!logLimit || logLimit[0] == '\0')
            return {GateStatus::MissingLogLimit, binarySha256};
        uint64_t parsedLogLimit = 0;
        if (!ParseUnsigned(logLimit, parsedLogLimit))
            return {GateStatus::MalformedLogLimit, binarySha256};
        if (parsedLogLimit == 0)
            return {GateStatus::ZeroLogLimit, binarySha256};
        if (parsedLogLimit > kMaxLogLimit)
            return {GateStatus::LogLimitTooLarge, binarySha256};

        if (!dispatchLimit || dispatchLimit[0] == '\0')
            return {GateStatus::MissingDispatchLimit, binarySha256};
        uint64_t parsedDispatchLimit = 0;
        if (!ParseUnsigned(dispatchLimit, parsedDispatchLimit))
            return {GateStatus::MalformedDispatchLimit, binarySha256};
        if (parsedDispatchLimit != 0)
            return {GateStatus::NonZeroDispatchLimit, binarySha256, parsedLogLimit, parsedDispatchLimit};

        return {GateStatus::Enabled, binarySha256, parsedLogLimit, parsedDispatchLimit};
    }

    bool IsReflectedLifecycleNameIndex(int32_t nameIndex)
    {
        return nameIndex == kCheckJoinInProgressNameIndex ||
            nameIndex == kHandleNewPlayerNameIndex ||
            nameIndex == kOnLogoutNameIndex;
    }

    bool IsLifecycleDiagnosticCandidateNameIndex(int32_t nameIndex)
    {
        return nameIndex == kGameModeK2PostLoginNameIndex ||
            nameIndex == kOnPostLoginDelegateNameIndex ||
            nameIndex == kOnStartNewPlayerDelegateNameIndex;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit)
    {
        return limit != 0 && counter.load(std::memory_order_relaxed) < limit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t limit,
                                     uint64_t& observationNumber)
    {
        if (limit == 0)
        {
            observationNumber = 0;
            return false;
        }

        uint64_t current = counter.load(std::memory_order_relaxed);
        while (current < limit)
        {
            if (counter.compare_exchange_weak(current,
                                              current + 1,
                                              std::memory_order_relaxed,
                                              std::memory_order_relaxed))
            {
                observationNumber = current + 1;
                return true;
            }
        }

        observationNumber = 0;
        return false;
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return limit != 0 && observationNumber != 0 && observationNumber <= limit;
    }

    uint32_t ApprovedRuntimeEvidenceLogRoleMask(const CopiedLifecycleObservation& observation)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        switch (observation.Role)
        {
        case LifecycleRole::SessionStart:
            if (observation.Function == LifecycleFunction::HandleNewPlayer &&
                observation.FunctionNameIndex == kHandleNewPlayerNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                observation.Action == PrincipalAction::CandidateCreated &&
                observation.BoolCount == 2 &&
                observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin &&
                observation.BoolStorage[0].Value &&
                observation.BoolStorage[1].Field == LifecycleField::ReturnValue &&
                observation.BoolStorage[1].Value &&
                HasCanonicalHandleNewPlayerRedactedSubjectShape(observation))
            {
                return 1u << 0;
            }
            return 0;
        case LifecycleRole::SessionStartRejected:
            if (observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic &&
                observation.FunctionNameIndex == kCheckJoinInProgressNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                observation.Action == PrincipalAction::None &&
                observation.BoolCount == 2 &&
                observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin &&
                observation.BoolStorage[0].Value &&
                observation.BoolStorage[1].Field == LifecycleField::ReturnValue &&
                !observation.BoolStorage[1].Value &&
                HasCanonicalCheckJoinRejectedRedactedShape(observation))
            {
                return 1u << 1;
            }
            return 0;
        case LifecycleRole::SessionEnd:
            if (observation.Function == LifecycleFunction::OnLogout &&
                observation.FunctionNameIndex == kOnLogoutNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                observation.Action == PrincipalAction::CandidateInvalidated &&
                observation.BoolCount == 0 &&
                HasCanonicalOnLogoutRedactedSubjectShape(observation))
            {
                return 1u << 2;
            }
            return 0;
        case LifecycleRole::DiagnosticOnly:
            return 0;
        }
        return 0;
    }

    bool TryReserveApprovedRuntimeEvidenceLogBudget(std::atomic<uint64_t>& counter,
                                                    std::atomic<uint32_t>& loggedRoleMask,
                                                    const CopiedLifecycleObservation& observation,
                                                    uint64_t limit,
                                                    uint64_t& observationNumber)
    {
        observationNumber = 0;
        const uint32_t roleMask = ApprovedRuntimeEvidenceLogRoleMask(observation);
        if (roleMask == 0 || !HasObservationBudgetRemaining(counter, limit))
            return false;

        uint32_t currentMask = loggedRoleMask.load(std::memory_order_relaxed);
        while ((currentMask & roleMask) == 0)
        {
            if (loggedRoleMask.compare_exchange_weak(currentMask,
                                                     currentMask | roleMask,
                                                     std::memory_order_relaxed,
                                                     std::memory_order_relaxed))
            {
                if (TryReserveObservationBudget(counter, limit, observationNumber))
                    return true;
                loggedRoleMask.fetch_and(~roleMask, std::memory_order_relaxed);
                observationNumber = 0;
                return false;
            }
        }

        return false;
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        return TryIdentifyInvocationWithTokenMode(
            gate,
            nameIndex,
            reader,
            function,
            params,
            Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::Assign);
    }

    Attempt TryIdentifyDiagnosticCandidateInvocation(
        const Gate& gate,
        int32_t nameIndex,
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        void* function,
        void* params)
    {
        if (!gate.Enabled())
            return {};

        if (nameIndex != kCheckJoinInProgressNameIndex &&
            nameIndex != kGameModeK2PostLoginNameIndex)
        {
            return {
                AttemptStatus::NonLifecycleFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::PlayerPrincipalLifecycleReflection::TryIdentifyLifecycleInvocation(
                reader,
                options,
                function,
                params,
                invocation,
                Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::Skip);
        }
        catch (...)
        {
            return {
                AttemptStatus::Rejected,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};
        const auto expectedFunction =
            nameIndex == kCheckJoinInProgressNameIndex
                ? Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::
                    CheckJoinInProgressDiagnostic
                : Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::
                    K2PostLoginDiagnostic;
        if (invocation.FunctionNameIndex != nameIndex ||
            invocation.Function != expectedFunction)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "player lifecycle diagnostic prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    bool TryIdentifyFunctionFNameNearMissDiagnostic(
        const Gate& gate,
        int32_t nameIndex,
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        void* function,
        FunctionFNameNearMissDiagnostic& out)
    {
        out = {};
        if (!gate.Enabled() ||
            IsReflectedLifecycleNameIndex(nameIndex) ||
            !function)
        {
            return false;
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        if (!options.Layout)
            return false;

        Obelisk::UE::RuntimeReflection::UFunctionView reflectedFunction;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::RuntimeReflection::TryReadUFunction(
                reader,
                options,
                function,
                reflectedFunction);
        }
        catch (...)
        {
            return false;
        }
        if (!result ||
            reflectedFunction.Object.NamePrivate.ComparisonIndex != nameIndex ||
            reflectedFunction.Object.NamePrivate.Number != 0)
        {
            return false;
        }

        const NearMissFunctionSpec* spec =
            MatchedNearMissLifecycleFunctionSpec(reader, *options.Layout, reflectedFunction);
        if (spec)
        {
            out.Function = spec->Function;
            out.ExpectedFunctionNameIndex = spec->NameIndex;
            out.ObservedFunctionNameIndex = reflectedFunction.Object.NamePrivate.ComparisonIndex;
            out.OuterNameIndex = spec->OuterNameIndex;
            out.Result = {
                Obelisk::UE::RuntimeReflection::ReadStatus::Ok,
                BuildFunctionFNameNearMissReason(*spec, out.ObservedFunctionNameIndex),
            };
            return true;
        }

        std::string rejectedReason;
        spec = MatchedRejectedNearMissLifecycleFunctionSpec(
            reader,
            *options.Layout,
            reflectedFunction,
            rejectedReason);
        if (!spec)
            return false;

        out.Function = spec->Function;
        out.ExpectedFunctionNameIndex = spec->NameIndex;
        out.ObservedFunctionNameIndex = reflectedFunction.Object.NamePrivate.ComparisonIndex;
        out.OuterNameIndex = spec->OuterNameIndex;
        out.Result = {
            Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
            std::move(rejectedReason),
        };
        return true;
    }

    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t& observationNumber,
                                 std::atomic<uint32_t>* approvedRuntimeEvidenceLoggedRoleMask)
    {
        observationNumber = 0;
        if (!gate.Enabled())
            return {};

        if (!IsReflectedLifecycleNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonLifecycleFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        if (!approvedRuntimeEvidenceLoggedRoleMask &&
            !HasObservationBudgetRemaining(observationCounter, gate.LogLimit))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        Attempt metadataAttempt = TryIdentifyInvocationWithTokenMode(
            gate,
            nameIndex,
            reader,
            function,
            params,
            Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::MetadataOnly);
        if (metadataAttempt.Status != AttemptStatus::Matched)
            return metadataAttempt;

        if (!approvedRuntimeEvidenceLoggedRoleMask &&
            !HasObservationBudgetRemaining(observationCounter, gate.LogLimit))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        Attempt validationAttempt = TryIdentifyInvocationWithTokenMode(
            gate,
            nameIndex,
            reader,
            function,
            params,
            Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::ValidateOnly);
        if (validationAttempt.Status != AttemptStatus::Matched)
            return validationAttempt;

        auto validationInvocation = validationAttempt.Invocation;
        ReplaceValidateOnlySubjectTokenSentinelForCopiedValidation(validationInvocation);

        CopiedLifecycleObservation validatedObservation;
        bool copiedObservationValid = false;
        try
        {
            copiedObservationValid =
                TryBuildCopiedLifecycleObservation(validationInvocation, validatedObservation);
        }
        catch (...)
        {
            copiedObservationValid = false;
        }
        if (!copiedObservationValid)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "player lifecycle copied observation rejected"),
                {},
            };
        }

        if (!approvedRuntimeEvidenceLoggedRoleMask &&
            !HasObservationBudgetRemaining(observationCounter, gate.LogLimit))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        Attempt finalAttempt = TryIdentifyInvocationWithTokenMode(
            gate,
            nameIndex,
            reader,
            function,
            params,
            Obelisk::UE::PlayerPrincipalLifecycleReflection::ProcessLocalSubjectTokenMode::Assign);
        if (finalAttempt.Status != AttemptStatus::Matched)
            return finalAttempt;

        CopiedLifecycleObservation finalObservation;
        bool finalCopiedObservationValid = false;
        try
        {
            finalCopiedObservationValid =
                TryBuildCopiedLifecycleObservation(finalAttempt.Invocation, finalObservation);
        }
        catch (...)
        {
            finalCopiedObservationValid = false;
        }
        if (!finalCopiedObservationValid)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "player lifecycle copied observation rejected"),
                {},
            };
        }

        if (approvedRuntimeEvidenceLoggedRoleMask)
        {
            observationNumber = 0;
        }
        else if (!TryReserveObservationBudget(observationCounter, gate.LogLimit, observationNumber))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        return finalAttempt;
    }

    bool TryBuildCopiedLifecycleObservation(
        const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation,
        CopiedLifecycleObservation& out)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        out = {};
        if (!HasRequiredLifecycleShapeAndPropertyNames(invocation))
            return false;

        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;

        if (invocation.OuterNameIndex != kShooterGameModeNameIndex)
        {
            out = {};
            return false;
        }

        switch (invocation.Function)
        {
        case LifecycleFunction::CheckJoinInProgressDiagnostic:
        {
            if (invocation.FunctionNameIndex != kCheckJoinInProgressNameIndex ||
                invocation.OuterNameIndex != kShooterGameModeNameIndex ||
                invocation.Fields.size() != 3 ||
                !invocation.HasParameterRanges)
            {
                out = {};
                return false;
            }

            bool sawBIsFromLogin = false;
            bool sawReturnValue = false;
            bool sawNewPlayer = false;
            bool isFromLogin = false;
            bool returnValue = false;
            for (const auto& field : invocation.Fields)
            {
                switch (field.Field)
                {
                case LifecycleField::BIsFromLogin:
                case LifecycleField::ReturnValue:
                {
                    LifecycleBoolObservation copied;
                    if (!TryCopyBool(field, copied) || !AddBoolField(copied, out))
                    {
                        out = {};
                        return false;
                    }
                    if (field.Field == LifecycleField::BIsFromLogin)
                    {
                        sawBIsFromLogin = true;
                        isFromLogin = copied.Value;
                    }
                    if (field.Field == LifecycleField::ReturnValue)
                    {
                        sawReturnValue = true;
                        returnValue = copied.Value;
                    }
                    break;
                }
                case LifecycleField::NewPlayer:
                    if (!field.Redacted || field.ExposesRange || !RedactedFieldHasNoCopiedPayload(field) ||
                        !AddRedactedField(field.Field, 0, out))
                    {
                        out = {};
                        return false;
                    }
                    sawNewPlayer = true;
                    break;
                case LifecycleField::PlayerData:
                case LifecycleField::PlayerCharacter:
                case LifecycleField::Exiting:
                    out = {};
                    return false;
                }
            }

            if (!sawBIsFromLogin ||
                !sawReturnValue ||
                !sawNewPlayer ||
                !isFromLogin ||
                returnValue ||
                out.BoolCount != 2 ||
                !HasCanonicalCheckJoinRejectedRedactedShape(out))
            {
                out = {};
                return false;
            }

            out.Role = LifecycleRole::SessionStartRejected;
            out.Action = PrincipalAction::None;
            return true;
        }
        case LifecycleFunction::K2PostLoginDiagnostic:
            out = {};
            return false;
        case LifecycleFunction::HandleNewPlayer:
        {
            if (invocation.FunctionNameIndex != kHandleNewPlayerNameIndex ||
                invocation.Fields.size() != 5 ||
                !invocation.HasParameterRanges)
            {
                out = {};
                return false;
            }

            bool sawBIsFromLogin = false;
            bool sawReturnValue = false;
            bool isFromLogin = false;
            bool returnValue = false;
            for (const auto& field : invocation.Fields)
            {
                switch (field.Field)
                {
                case LifecycleField::NewPlayer:
                case LifecycleField::PlayerData:
                case LifecycleField::PlayerCharacter:
                    if (!field.Redacted || field.ExposesRange || !RedactedFieldHasNoCopiedPayload(field) ||
                        !AddRedactedField(field.Field, CopyableProcessLocalSubjectToken(field), out))
                    {
                        out = {};
                        return false;
                    }
                    break;
                case LifecycleField::BIsFromLogin:
                case LifecycleField::ReturnValue:
                {
                    LifecycleBoolObservation copied;
                    if (!TryCopyBool(field, copied) || !AddBoolField(copied, out))
                    {
                        out = {};
                        return false;
                    }
                    if (field.Field == LifecycleField::BIsFromLogin)
                    {
                        sawBIsFromLogin = true;
                        isFromLogin = copied.Value;
                    }
                    if (field.Field == LifecycleField::ReturnValue)
                    {
                        sawReturnValue = true;
                        returnValue = copied.Value;
                    }
                    break;
                }
                case LifecycleField::Exiting:
                    out = {};
                    return false;
                }
            }

            if (!sawBIsFromLogin ||
                !sawReturnValue ||
                out.BoolCount != 2 ||
                !HasCanonicalHandleNewPlayerRedactedSubjectShape(out))
            {
                out = {};
                return false;
            }

            if (!isFromLogin)
            {
                out = {};
                return false;
            }

            if (!returnValue)
            {
                out = {};
                return false;
            }

            out.Role = LifecycleRole::SessionStart;
            out.Action = PrincipalAction::CandidateCreated;
            return true;
        }
        case LifecycleFunction::OnLogout:
            if (invocation.FunctionNameIndex != kOnLogoutNameIndex ||
                invocation.Fields.size() != 1 ||
                !invocation.HasParameterRanges)
            {
                out = {};
                return false;
            }
            if (invocation.Fields[0].Field != LifecycleField::Exiting ||
                !invocation.Fields[0].Redacted ||
                invocation.Fields[0].ExposesRange ||
                !RedactedFieldHasNoCopiedPayload(invocation.Fields[0]) ||
                !AddRedactedField(LifecycleField::Exiting,
                                  CopyableProcessLocalSubjectToken(invocation.Fields[0]),
                                  out) ||
                !HasCanonicalOnLogoutRedactedSubjectShape(out))
            {
                out = {};
                return false;
            }
            out.Role = LifecycleRole::SessionEnd;
            out.Action = PrincipalAction::CandidateInvalidated;
            return true;
        }

        out = {};
        return false;
    }

    bool TryBuildCopiedLifecycleDiagnosticObservation(
        const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation,
        CopiedLifecycleObservation& out)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        out = {};
        if (!HasRequiredLifecycleShapeAndPropertyNames(invocation))
            return false;

        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;

        if (invocation.Function == LifecycleFunction::K2PostLoginDiagnostic)
        {
            if (invocation.FunctionNameIndex != kGameModeK2PostLoginNameIndex ||
                invocation.OuterNameIndex != kGameModeNameIndex ||
                invocation.Fields.size() != 1)
            {
                out = {};
                return false;
            }
            const auto& field = invocation.Fields[0];
            if (field.Field != LifecycleField::NewPlayer ||
                !field.Redacted ||
                field.ExposesRange ||
                !RedactedFieldHasNoCopiedPayload(field) ||
                !AddRedactedField(field.Field, CopyableProcessLocalSubjectToken(field), out))
            {
                out = {};
                return false;
            }
            out.Role = LifecycleRole::DiagnosticOnly;
            out.Action = PrincipalAction::None;
            return true;
        }

        if (invocation.Function != LifecycleFunction::CheckJoinInProgressDiagnostic ||
            invocation.FunctionNameIndex != kCheckJoinInProgressNameIndex ||
            invocation.OuterNameIndex != kShooterGameModeNameIndex ||
            invocation.Fields.size() != 3 ||
            !invocation.HasParameterRanges)
        {
            out = {};
            return false;
        }

        bool sawBIsFromLogin = false;
        bool sawReturnValue = false;
        bool sawNewPlayer = false;
        bool isFromLogin = false;
        bool returnValue = false;
        for (const auto& field : invocation.Fields)
        {
            switch (field.Field)
            {
            case LifecycleField::BIsFromLogin:
            case LifecycleField::ReturnValue:
            {
                LifecycleBoolObservation copied;
                if (!TryCopyBool(field, copied) || !AddBoolField(copied, out))
                {
                    out = {};
                    return false;
                }
                if (field.Field == LifecycleField::BIsFromLogin)
                {
                    sawBIsFromLogin = true;
                    isFromLogin = copied.Value;
                }
                if (field.Field == LifecycleField::ReturnValue)
                {
                    sawReturnValue = true;
                    returnValue = copied.Value;
                }
                break;
            }
            case LifecycleField::NewPlayer:
                if (!field.Redacted || field.ExposesRange || !RedactedFieldHasNoCopiedPayload(field) ||
                    !AddRedactedField(field.Field, 0, out))
                {
                    out = {};
                    return false;
                }
                sawNewPlayer = true;
                break;
            case LifecycleField::PlayerData:
            case LifecycleField::PlayerCharacter:
            case LifecycleField::Exiting:
                out = {};
                return false;
            }
        }

        if (!sawBIsFromLogin || !sawReturnValue || !sawNewPlayer ||
            out.BoolCount != 2 || out.RedactedCount != 1)
        {
            out = {};
            return false;
        }
        if (isFromLogin && !returnValue)
        {
            out = {};
            return false;
        }

        out.Role = LifecycleRole::DiagnosticOnly;
        out.Action = PrincipalAction::None;
        return true;
    }

    bool TryBuildCopiedLifecycleObservationAfterOriginal(bool originalWasCalled,
                                                         const Attempt& attempt,
                                                         CopiedLifecycleObservation& out)
    {
        out = {};
        if (!originalWasCalled || attempt.Status != AttemptStatus::Matched || !attempt.Result)
            return false;
        return TryBuildCopiedLifecycleObservation(attempt.Invocation, out);
    }

    bool TryMapPlayerPrincipalEventKind(LifecycleRole role,
                                        Obelisk::Core::PlayerPrincipalEventKind& out)
    {
        switch (role)
        {
        case LifecycleRole::SessionStart:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
            return true;
        case LifecycleRole::SessionStartRejected:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected;
            return true;
        case LifecycleRole::SessionEnd:
            out = Obelisk::Core::PlayerPrincipalEventKind::SessionEnd;
            return true;
        case LifecycleRole::DiagnosticOnly:
            return false;
        }
        return false;
    }

    bool TryMapPlayerPrincipalAction(PrincipalAction action,
                                     Obelisk::Core::PlayerPrincipalAction& out)
    {
        switch (action)
        {
        case PrincipalAction::None:
            out = Obelisk::Core::PlayerPrincipalAction::None;
            return true;
        case PrincipalAction::CandidateCreated:
            out = Obelisk::Core::PlayerPrincipalAction::CandidateCreated;
            return true;
        case PrincipalAction::CandidateInvalidated:
            out = Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated;
            return true;
        }
        return false;
    }

    bool TryBuildPlayerPrincipalEventView(
        const CopiedLifecycleObservation& observation,
        std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2>& boolStorage,
        Obelisk::Core::PlayerPrincipalEventView& out)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        out = {};

        Obelisk::Core::PlayerPrincipalEventKind kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
        if (!TryMapPlayerPrincipalEventKind(observation.Role, kind))
            return false;

        Obelisk::Core::PlayerPrincipalAction action =
            Obelisk::Core::PlayerPrincipalAction::None;
        if (!TryMapPlayerPrincipalAction(observation.Action, action))
            return false;

        switch (observation.Role)
        {
        case LifecycleRole::SessionStart:
        {
            if (observation.Function != LifecycleFunction::HandleNewPlayer ||
                observation.FunctionNameIndex != kHandleNewPlayerNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 2 ||
                !HasCanonicalHandleNewPlayerRedactedSubjectShape(observation))
            {
                return false;
            }

            if (observation.BoolStorage[0].Field != LifecycleField::BIsFromLogin ||
                observation.BoolStorage[1].Field != LifecycleField::ReturnValue)
            {
                return false;
            }

            const bool acceptedStart =
                observation.BoolStorage[0].Value && observation.BoolStorage[1].Value;
            if (!acceptedStart ||
                observation.Action != PrincipalAction::CandidateCreated ||
                action != Obelisk::Core::PlayerPrincipalAction::CandidateCreated)
            {
                return false;
            }

            for (size_t i = 0; i < observation.BoolCount; ++i)
            {
                Obelisk::Core::PlayerPrincipalBoolField mappedField =
                    Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin;
                if (!TryMapPlayerPrincipalBoolField(observation.BoolStorage[i].Field, mappedField))
                    return false;

                boolStorage[i] = {
                    .Field = mappedField,
                    .Value = observation.BoolStorage[i].Value,
                };
            }

            out = {
                .Kind = kind,
                .Action = action,
                .EventSequence = 0,
                .ServerProcessEpoch = 0,
                .Bools = std::span<const Obelisk::Core::PlayerPrincipalBoolValue>(
                    boolStorage.data(),
                    observation.BoolCount),
            };
            return true;
        }
        case LifecycleRole::SessionStartRejected:
        {
            if (observation.Action != PrincipalAction::None ||
                action != Obelisk::Core::PlayerPrincipalAction::None ||
                observation.BoolCount != 2 ||
                observation.BoolStorage[0].Field != LifecycleField::BIsFromLogin ||
                observation.BoolStorage[1].Field != LifecycleField::ReturnValue)
            {
                return false;
            }

            if (observation.Function != LifecycleFunction::CheckJoinInProgressDiagnostic ||
                observation.FunctionNameIndex != kCheckJoinInProgressNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                !HasCanonicalCheckJoinRejectedRedactedShape(observation) ||
                !observation.BoolStorage[0].Value ||
                observation.BoolStorage[1].Value)
            {
                return false;
            }

            for (size_t i = 0; i < observation.BoolCount; ++i)
            {
                Obelisk::Core::PlayerPrincipalBoolField mappedField =
                    Obelisk::Core::PlayerPrincipalBoolField::BIsFromLogin;
                if (!TryMapPlayerPrincipalBoolField(observation.BoolStorage[i].Field, mappedField))
                    return false;

                boolStorage[i] = {
                    .Field = mappedField,
                    .Value = observation.BoolStorage[i].Value,
                };
            }

            out = {
                .Kind = kind,
                .Action = action,
                .EventSequence = 0,
                .ServerProcessEpoch = 0,
                .Bools = std::span<const Obelisk::Core::PlayerPrincipalBoolValue>(
                    boolStorage.data(),
                    observation.BoolCount),
            };
            return true;
        }
        case LifecycleRole::SessionEnd:
            if (observation.Function != LifecycleFunction::OnLogout ||
                observation.FunctionNameIndex != kOnLogoutNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 0 ||
                observation.Action != PrincipalAction::CandidateInvalidated ||
                action != Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated ||
                !HasCanonicalOnLogoutRedactedSubjectShape(observation))
            {
                return false;
            }

            out = {
                .Kind = kind,
                .Action = action,
                .EventSequence = 0,
                .ServerProcessEpoch = 0,
                .Bools = {},
            };
            return true;
        case LifecycleRole::DiagnosticOnly:
            return false;
        }

        return false;
    }

    const char* LifecycleFunctionName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
        switch (function)
        {
        case LifecycleFunction::CheckJoinInProgressDiagnostic:
            return "CheckJoinInProgressDiagnostic";
        case LifecycleFunction::K2PostLoginDiagnostic:
            return "K2PostLoginDiagnostic";
        case LifecycleFunction::HandleNewPlayer:
            return "HandleNewPlayer";
        case LifecycleFunction::OnLogout:
            return "OnLogout";
        }
        return "Unknown";
    }

    const char* LifecycleTargetName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
        switch (function)
        {
        case LifecycleFunction::CheckJoinInProgressDiagnostic:
            return "ShooterGameMode.CheckJoinInProgress";
        case LifecycleFunction::K2PostLoginDiagnostic:
            return "GameMode.K2_PostLogin";
        case LifecycleFunction::HandleNewPlayer:
            return "ShooterGameMode.HandleNewPlayer";
        case LifecycleFunction::OnLogout:
            return "ShooterGameMode.OnLogout";
        }
        return "Unknown.Unknown";
    }

    const char* LifecycleDiagnosticCandidateTargetName(int32_t nameIndex)
    {
        switch (nameIndex)
        {
        case kCheckJoinInProgressNameIndex:
            return "ShooterGameMode.CheckJoinInProgress";
        case kHandleNewPlayerNameIndex:
            return "ShooterGameMode.HandleNewPlayer";
        case kOnLogoutNameIndex:
            return "ShooterGameMode.OnLogout";
        case kGameModeK2PostLoginNameIndex:
            return "GameMode.K2_PostLogin";
        case kOnPostLoginDelegateNameIndex:
            return "ShooterGameMode.OnPostLogin__DelegateSignature";
        case kOnStartNewPlayerDelegateNameIndex:
            return "ShooterGameMode.OnStartNewPlayer__DelegateSignature";
        }
        return "Unknown.Unknown";
    }

    const char* LifecycleFieldName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field)
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        switch (field)
        {
        case LifecycleField::NewPlayer:
            return "NewPlayer";
        case LifecycleField::PlayerData:
            return "PlayerData";
        case LifecycleField::PlayerCharacter:
            return "PlayerCharacter";
        case LifecycleField::BIsFromLogin:
            return "bIsFromLogin";
        case LifecycleField::ReturnValue:
            return "ReturnValue";
        case LifecycleField::Exiting:
            return "Exiting";
        }
        return "Unknown";
    }

    const char* LifecycleRoleName(LifecycleRole role)
    {
        switch (role)
        {
        case LifecycleRole::SessionStart:
            return "session_start";
        case LifecycleRole::SessionEnd:
            return "session_end";
        case LifecycleRole::SessionStartRejected:
            return "session_start_rejected";
        case LifecycleRole::DiagnosticOnly:
            return "diagnostic_only";
        }
        return "unknown";
    }

    const char* PrincipalActionName(PrincipalAction action)
    {
        switch (action)
        {
        case PrincipalAction::CandidateCreated:
            return "candidate_created";
        case PrincipalAction::CandidateInvalidated:
            return "candidate_invalidated";
        case PrincipalAction::None:
            return "none";
        }
        return "none";
    }
}
