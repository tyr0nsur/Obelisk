#include "PlayerPrincipalLifecycleReflection.h"

#include <array>
#include <cctype>
#include <cstring>
#include <limits>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>

namespace Obelisk::UE::PlayerPrincipalLifecycleReflection
{
    namespace
    {
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

        constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
        constexpr uint32_t kK2PostLoginFunctionFlags = 0x0c020800;
        constexpr uint32_t kCheckJoinInProgressFunctionFlags = 0x0c080c00;
        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;

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
        constexpr size_t kMaxDiagnosticReasonLength = 768;
        constexpr std::string_view kTruncatedDiagnosticSuffix = "_truncated";
        static_assert(kMaxDiagnosticReasonLength > kTruncatedDiagnosticSuffix.size());

        struct ProcessLocalSubjectTokenState
        {
            std::mutex Mutex;
            uint64_t NextToken = 1;
            std::unordered_map<uint64_t, uint64_t> TokensByObjectFingerprint;
        };

        ProcessLocalSubjectTokenState& GetProcessLocalSubjectTokenState()
        {
            static auto* state = new ProcessLocalSubjectTokenState();
            return *state;
        }

        struct LifecycleFieldSpec
        {
            LifecycleField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            uint64_t PropertyFlags;
            bool ExposesRange;
            bool Redacted;
        };

        struct LifecycleFunctionSpec
        {
            LifecycleFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            int32_t OuterObjectIndex;
            uint32_t FunctionFlags;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const LifecycleFieldSpec* Fields;
            size_t FieldCount;
        };

        struct BoolPropertyMetadata
        {
            uint8_t FieldSize = 0;
            uint8_t ByteOffset = 0;
            uint8_t ByteMask = 0;
            uint8_t FieldMask = 0;
        };

        constexpr std::array<LifecycleFieldSpec, 3> kCheckJoinInProgressFields{{
            {LifecycleField::BIsFromLogin,
             kBIsFromLoginNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true,
             false},
            {LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::ReturnValue,
             kReturnValueNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true,
             false},
        }};

        constexpr std::array<LifecycleFieldSpec, 1> kK2PostLoginFields{{
            {LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
        }};

        constexpr std::array<LifecycleFieldSpec, 5> kHandleNewPlayerFields{{
            {LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::PlayerData,
             kPlayerDataNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::PlayerCharacter,
             kPlayerCharacterNameIndex,
             0x10,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::BIsFromLogin,
             kBIsFromLoginNameIndex,
             0x18,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true,
             false},
            {LifecycleField::ReturnValue,
             kReturnValueNameIndex,
             0x19,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true,
             false},
        }};

        constexpr std::array<LifecycleFieldSpec, 1> kOnLogoutFields{{
            {LifecycleField::Exiting,
             kExitingNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
        }};

        constexpr LifecycleFunctionSpec kCheckJoinInProgressSpec{
            LifecycleFunction::CheckJoinInProgressDiagnostic,
            kCheckJoinInProgressNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kCheckJoinInProgressFunctionFlags,
            3,
            0x11,
            0x10,
            kCheckJoinInProgressFields.data(),
            kCheckJoinInProgressFields.size(),
        };

        constexpr LifecycleFunctionSpec kHandleNewPlayerSpec{
            LifecycleFunction::HandleNewPlayer,
            kHandleNewPlayerNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            5,
            0x1a,
            0x19,
            kHandleNewPlayerFields.data(),
            kHandleNewPlayerFields.size(),
        };

        constexpr LifecycleFunctionSpec kK2PostLoginSpec{
            LifecycleFunction::K2PostLoginDiagnostic,
            kGameModeK2PostLoginNameIndex,
            kGameModeNameIndex,
            kGameModeObjectIndex,
            kK2PostLoginFunctionFlags,
            1,
            0x08,
            0xffff,
            kK2PostLoginFields.data(),
            kK2PostLoginFields.size(),
        };

        constexpr LifecycleFunctionSpec kOnLogoutSpec{
            LifecycleFunction::OnLogout,
            kOnLogoutNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            1,
            0x08,
            0xffff,
            kOnLogoutFields.data(),
            kOnLogoutFields.size(),
        };

        const LifecycleFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kCheckJoinInProgressNameIndex:
                return &kCheckJoinInProgressSpec;
            case kGameModeK2PostLoginNameIndex:
                return &kK2PostLoginSpec;
            case kHandleNewPlayerNameIndex:
                return &kHandleNewPlayerSpec;
            case kOnLogoutNameIndex:
                return &kOnLogoutSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "player principal lifecycle reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for player principal lifecycle reflection");
            const RuntimeReflection::FieldLayout* supportedLayout =
                RuntimeReflection::FindSupportedLayout(RuntimeReflection::kSupportedShooterGameServerSha256);
            if (options.Layout != supportedLayout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "player principal lifecycle constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ReadByteAt(const RuntimeReflection::MemoryReader& reader,
                                                 const void* base,
                                                 size_t offset,
                                                 uint8_t& out)
        {
            if (!base)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                           "null lifecycle bool property base");
            const auto* address = reinterpret_cast<const uint8_t*>(base) + offset;
            if (!reader.CanRead(address, sizeof(uint8_t)))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Unreadable,
                                                           "lifecycle bool property metadata is unreadable");
            std::memcpy(&out, address, sizeof(uint8_t));
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ReadBoolPropertyMetadata(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::UPropertyView& property,
                                                               BoolPropertyMetadata& out)
        {
            BoolPropertyMetadata value;
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyFieldSizeOffset, value.FieldSize);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyByteOffsetOffset, value.ByteOffset);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyByteMaskOffset, value.ByteMask);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyFieldMaskOffset, value.FieldMask);
                !result)
            {
                return result;
            }
            out = value;
            return RuntimeReflection::ReadResult::Ok();
        }

        void AppendKeyValue(std::string& reason, std::string_view key, std::string_view value)
        {
            reason += "_";
            reason += key;
            reason += "_";
            reason += value;
        }

        void AppendKeyValueSigned(std::string& reason, std::string_view key, int64_t value)
        {
            AppendKeyValue(reason, key, std::to_string(value));
        }

        void AppendKeyValueUnsigned(std::string& reason, std::string_view key, uint64_t value)
        {
            AppendKeyValue(reason, key, std::to_string(value));
        }

        std::string SanitizeReasonToken(std::string_view value)
        {
            std::string token;
            token.reserve(value.size());
            for (unsigned char character : value)
            {
                if (std::isalnum(character) || character == '_' || character == '.' ||
                    character == ':' || character == '-')
                {
                    token.push_back(static_cast<char>(character));
                }
                else
                {
                    token.push_back('_');
                }
            }
            return token.empty() ? "unknown" : token;
        }

        bool ContainsForbiddenDiagnosticFragment(std::string_view token)
        {
            std::string normalized;
            normalized.reserve(token.size());
            for (unsigned char character : token)
            {
                if (std::isalnum(character))
                    normalized.push_back(static_cast<char>(std::tolower(character)));
            }

            return normalized.find("classobject") != std::string::npos ||
                normalized.find("identity") != std::string::npos ||
                normalized.find("params") != std::string::npos ||
                normalized.find("pointer") != std::string::npos;
        }

        std::string BoundDiagnosticReason(std::string reason)
        {
            if (reason.size() <= kMaxDiagnosticReasonLength)
                return reason;

            reason.resize(kMaxDiagnosticReasonLength - kTruncatedDiagnosticSuffix.size());
            reason += kTruncatedDiagnosticSuffix;
            return reason;
        }

        std::string SafeDiagnosticReasonToken(std::string_view value)
        {
            std::string token = SanitizeReasonToken(value);
            if (ContainsForbiddenDiagnosticFragment(token))
                return "lifecycle_reflection_rejected";
            return BoundDiagnosticReason(std::move(token));
        }

        RuntimeReflection::ReadResult SafeDiagnosticFailure(RuntimeReflection::ReadStatus status,
                                                            std::string_view reason)
        {
            return RuntimeReflection::ReadResult::Fail(status, SafeDiagnosticReasonToken(reason));
        }

        RuntimeReflection::ReadResult SafeDiagnosticFailure(const RuntimeReflection::ReadResult& result)
        {
            return SafeDiagnosticFailure(result.Status, result.Reason);
        }

        std::string_view LifecycleTargetName(LifecycleFunction function)
        {
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

        void AppendExpectedPropertyNameIndexChain(std::string& reason,
                                                  const LifecycleFunctionSpec& spec)
        {
            reason += "_expected_property_name_indices";
            for (size_t index = 0; index < spec.FieldCount; ++index)
            {
                reason += index == 0 ? "_" : ".";
                reason += std::to_string(spec.Fields[index].NameIndex);
            }
        }

        void AppendObservedPropertyNameIndexChain(std::string& reason,
                                                  const RuntimeReflection::UFunctionView& function)
        {
            reason += "_observed_property_name_indices";
            for (size_t index = 0; index < function.Parameters.size(); ++index)
            {
                reason += index == 0 ? "_" : ".";
                reason += std::to_string(function.Parameters[index].Object.NamePrivate.ComparisonIndex);
            }
        }

        void AppendObservedPropertyFNameChain(std::string& reason,
                                              const RuntimeReflection::UFunctionView& function)
        {
            reason += "_observed_property_fname_chain=";
            if (function.Parameters.empty())
            {
                reason += "none";
                return;
            }
            for (size_t index = 0; index < function.Parameters.size(); ++index)
            {
                if (index != 0)
                    reason += ".";
                reason += std::to_string(function.Parameters[index].Object.NamePrivate.ComparisonIndex);
            }
        }

        void AppendObservedPropertyFNameChain(std::string& reason,
                                              const LifecycleInvocation& invocation)
        {
            reason += "_observed_property_fname_chain=";
            if (invocation.Fields.empty())
            {
                reason += "none";
                return;
            }
            for (size_t index = 0; index < invocation.Fields.size(); ++index)
            {
                if (index != 0)
                    reason += ".";
                reason += std::to_string(invocation.Fields[index].PropertyNameIndex);
            }
        }

        bool IsCurrentRuntimeUnapprovedPropertyFNameDrift(const LifecycleFunctionSpec& spec,
                                                          size_t position,
                                                          int32_t expectedNameIndex,
                                                          int32_t observedNameIndex)
        {
            if (position != 0 ||
                static_cast<int64_t>(observedNameIndex) -
                        static_cast<int64_t>(expectedNameIndex) !=
                    11)
            {
                return false;
            }

            switch (spec.Function)
            {
            case LifecycleFunction::HandleNewPlayer:
            case LifecycleFunction::K2PostLoginDiagnostic:
                return expectedNameIndex == kNewPlayerNameIndex &&
                    observedNameIndex == kNewPlayerNameIndex + 11;
            case LifecycleFunction::OnLogout:
                return expectedNameIndex == kExitingNameIndex &&
                    observedNameIndex == kExitingNameIndex + 11;
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
                return expectedNameIndex == kBIsFromLoginNameIndex &&
                    observedNameIndex == kBIsFromLoginNameIndex + 11;
            }
            return false;
        }

        void AppendCurrentRuntimeUnapprovedDriftDiagnostic(
            std::string& reason,
            const LifecycleFunctionSpec& spec,
            const RuntimeReflection::UFunctionView& function,
            size_t position,
            int32_t expectedNameIndex,
            int32_t observedNameIndex)
        {
            if (!IsCurrentRuntimeUnapprovedPropertyFNameDrift(spec,
                                                              position,
                                                              expectedNameIndex,
                                                              observedNameIndex))
            {
                return;
            }

            AppendKeyValue(reason, "diagnostic", "current_runtime_unapproved_fname_drift");
            AppendKeyValue(reason,
                           "offline_source_required",
                           "redacted_ufunction_snapshot_and_fname_manifest");
            AppendKeyValue(reason, "target", LifecycleTargetName(spec.Function));
            AppendKeyValue(reason, "disposition", "reject_only");
            AppendKeyValueUnsigned(reason, "mismatch_position", position);
            AppendKeyValueSigned(reason,
                                 "mismatch_delta",
                                 static_cast<int64_t>(observedNameIndex) -
                                     static_cast<int64_t>(expectedNameIndex));
            AppendExpectedPropertyNameIndexChain(reason, spec);
            AppendObservedPropertyNameIndexChain(reason, function);
        }

        void AppendObservedPropertyMetadata(const RuntimeReflection::MemoryReader& reader,
                                            const RuntimeReflection::FieldLayout& layout,
                                            const RuntimeReflection::UPropertyView& property,
                                            size_t index,
                                            std::string& reason)
        {
            std::string prefix = "prop_";
            prefix += std::to_string(index);

            AppendKeyValueSigned(reason, prefix + "_name_index", property.Object.NamePrivate.ComparisonIndex);
            AppendKeyValueSigned(reason, prefix + "_number", property.Object.NamePrivate.Number);
            AppendKeyValueSigned(reason, prefix + "_offset", property.OffsetInternal);
            AppendKeyValueUnsigned(reason, prefix + "_size", static_cast<uint64_t>(property.ByteSize));
            AppendKeyValueSigned(reason, prefix + "_element_size", property.ElementSize);
            AppendKeyValueSigned(reason, prefix + "_array_dim", property.ArrayDim);
            AppendKeyValueUnsigned(reason, prefix + "_flags", property.PropertyFlags);

            RuntimeReflection::UObjectView propertyClass;
            if (property.Object.ClassPrivate &&
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass))
            {
                AppendKeyValueSigned(reason, prefix + "_class_name_index", propertyClass.NamePrivate.ComparisonIndex);
                AppendKeyValueSigned(reason, prefix + "_class_number", propertyClass.NamePrivate.Number);

                if (propertyClass.NamePrivate.ComparisonIndex == kBoolPropertyClassNameIndex &&
                    propertyClass.NamePrivate.Number == 0)
                {
                    BoolPropertyMetadata metadata;
                    if (ReadBoolPropertyMetadata(reader, property, metadata))
                    {
                        AppendKeyValueSigned(reason, prefix + "_bool_field_size", metadata.FieldSize);
                        AppendKeyValueSigned(reason, prefix + "_bool_byte_offset", metadata.ByteOffset);
                        AppendKeyValueSigned(reason, prefix + "_bool_byte_mask", metadata.ByteMask);
                        AppendKeyValueSigned(reason, prefix + "_bool_field_mask", metadata.FieldMask);
                    }
                    else
                    {
                        reason += "_";
                        reason += prefix;
                        reason += "_bool_metadata_unreadable";
                    }
                }
            }
            else
            {
                reason += "_";
                reason += prefix;
                reason += "_class_unreadable";
            }
        }

        std::string BuildPropertyValidationMismatchReason(
            const RuntimeReflection::MemoryReader& reader,
            const RuntimeReflection::FieldLayout& layout,
            const RuntimeReflection::UFunctionView& function,
            const LifecycleFunctionSpec& functionSpec,
            const RuntimeReflection::UPropertyView& property,
            size_t position,
            const LifecycleFieldSpec& spec,
            std::string_view cause)
        {
            std::string reason = "lifecycle_property_validation_mismatch";
            reason += "_cause_";
            reason += SafeDiagnosticReasonToken(cause);
            AppendObservedPropertyFNameChain(reason, function);
            AppendCurrentRuntimeUnapprovedDriftDiagnostic(reason,
                                                          functionSpec,
                                                          function,
                                                          position,
                                                          spec.NameIndex,
                                                          property.Object.NamePrivate.ComparisonIndex);
            AppendKeyValueSigned(reason, "expected_name", spec.NameIndex);
            AppendKeyValueSigned(reason, "observed_name", property.Object.NamePrivate.ComparisonIndex);
            AppendKeyValueSigned(reason, "expected_offset", spec.Offset);
            AppendKeyValueSigned(reason, "observed_offset", property.OffsetInternal);
            AppendKeyValueUnsigned(reason, "expected_size", static_cast<uint64_t>(spec.Size));
            AppendKeyValueUnsigned(reason, "observed_size", static_cast<uint64_t>(property.ByteSize));
            AppendKeyValueSigned(reason, "expected_element_size", static_cast<int64_t>(spec.Size));
            AppendKeyValueSigned(reason, "observed_element_size", property.ElementSize);
            AppendKeyValueSigned(reason, "expected_array_dim", 1);
            AppendKeyValueSigned(reason, "observed_array_dim", property.ArrayDim);
            AppendKeyValueUnsigned(reason, "expected_flags", spec.PropertyFlags);
            AppendKeyValueUnsigned(reason, "observed_flags", property.PropertyFlags);
            AppendKeyValueSigned(reason, "expected_class_name", spec.ClassNameIndex);

            RuntimeReflection::UObjectView propertyClass;
            if (property.Object.ClassPrivate &&
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass))
            {
                AppendKeyValueSigned(reason, "observed_class_name", propertyClass.NamePrivate.ComparisonIndex);
            }
            else
            {
                reason += "_observed_class_unreadable";
            }

            if (spec.ClassNameIndex == kBoolPropertyClassNameIndex)
            {
                BoolPropertyMetadata metadata;
                if (ReadBoolPropertyMetadata(reader, property, metadata))
                {
                    AppendKeyValueSigned(reason, "bool_field_size", metadata.FieldSize);
                    AppendKeyValueSigned(reason, "bool_byte_offset", metadata.ByteOffset);
                    AppendKeyValueSigned(reason, "bool_byte_mask", metadata.ByteMask);
                    AppendKeyValueSigned(reason, "bool_field_mask", metadata.FieldMask);
                }
                else
                {
                    reason += "_bool_metadata_unreadable";
                }
            }

            return BoundDiagnosticReason(std::move(reason));
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction class FName mismatch");
            if (functionClass.InternalIndex != kFunctionClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const LifecycleFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match lifecycle spec");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction FunctionFlags mismatch");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const LifecycleFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction outer FName mismatch");
            if (outer.InternalIndex != spec.OuterObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction outer object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const LifecycleFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const LifecycleFieldSpec& spec,
                                                       bool requireNameMatch)
        {
            if (requireNameMatch &&
                (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                 property.Object.NamePrivate.Number != 0))
            {
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property FName mismatch");
            }
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property ArrayDim mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property flags mismatch");
            if (RuntimeReflection::ReadResult result = ValidatePropertyClass(reader, layout, property, spec); !result)
                return result;
            if (spec.ClassNameIndex == kBoolPropertyClassNameIndex)
            {
                BoolPropertyMetadata metadata;
                if (RuntimeReflection::ReadResult result = ReadBoolPropertyMetadata(reader, property, metadata);
                    !result)
                {
                    return result;
                }
                if (metadata.FieldSize != kBoolFieldSize ||
                    metadata.ByteOffset != kBoolByteOffset ||
                    metadata.ByteMask != kBoolByteMask ||
                    metadata.FieldMask != kBoolFieldMask)
                {
                    return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                               "lifecycle bool property metadata mismatch");
                }
            }
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult CopyCanonicalBool(const RuntimeReflection::ParamRange& range,
                                                        uint8_t& out)
        {
            out = 0;
            if (!range.Data || range.Size != sizeof(uint8_t))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle bool range is not a single byte");

            uint8_t value = 0;
            std::memcpy(&value, range.Data, sizeof(value));
            if (value > 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle bool byte is not canonical");
            out = value;
            return RuntimeReflection::ReadResult::Ok();
        }

        bool IsCanonicalUserPointer(uintptr_t address)
        {
            return address >= 0x10000 && address <= 0x00007FFFFFFFFFFF;
        }

        uint64_t MixProcessLocalValue(uint64_t value)
        {
            value += 0x9e3779b97f4a7c15ULL;
            value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
            value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
            return value ^ (value >> 31U);
        }

        uint64_t ProcessLocalSubjectFingerprint(uintptr_t objectAddress,
                                                const ProcessLocalSubjectTokenState& state)
        {
            const uint64_t salt = MixProcessLocalValue(static_cast<uint64_t>(
                reinterpret_cast<uintptr_t>(&state)));
            uint64_t fingerprint = MixProcessLocalValue(static_cast<uint64_t>(objectAddress) ^ salt);
            if (fingerprint == 0)
                fingerprint = MixProcessLocalValue(salt ^ 0xd6e8feb86659fd93ULL);
            return fingerprint == 0 ? 1 : fingerprint;
        }

        bool IsAssignableProcessLocalSubjectToken(uint64_t token)
        {
            return token != 0 && token != std::numeric_limits<uint64_t>::max();
        }

        uint64_t AssignProcessLocalSubjectToken(uintptr_t objectAddress)
        {
            if (!IsCanonicalUserPointer(objectAddress))
                return 0;

            auto& state = GetProcessLocalSubjectTokenState();
            // Keep only a process-local keyed fingerprint, never the raw UE object
            // address, while preserving same-process correlation.
            const uint64_t objectFingerprint = ProcessLocalSubjectFingerprint(objectAddress, state);
            std::lock_guard<std::mutex> lock(state.Mutex);
            const auto existing = state.TokensByObjectFingerprint.find(objectFingerprint);
            if (existing != state.TokensByObjectFingerprint.end())
                return existing->second;

            if (!IsAssignableProcessLocalSubjectToken(state.NextToken))
                return 0;

            const uint64_t token = state.NextToken;
            if (state.NextToken == std::numeric_limits<uint64_t>::max() - 1)
                state.NextToken = 0;
            else
                ++state.NextToken;

            state.TokensByObjectFingerprint.emplace(objectFingerprint, token);
            return token;
        }

        bool UsesProcessLocalSubjectToken(LifecycleFunction function, LifecycleField field)
        {
            switch (function)
            {
            case LifecycleFunction::HandleNewPlayer:
                return field == LifecycleField::NewPlayer;
            case LifecycleFunction::OnLogout:
                return field == LifecycleField::Exiting;
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
            case LifecycleFunction::K2PostLoginDiagnostic:
                return false;
            }
            return false;
        }

        RuntimeReflection::ReadResult TryAssignProcessLocalSubjectToken(
            const RuntimeReflection::MemoryReader& reader,
            const void* params,
            uint16_t parmsSize,
            const RuntimeReflection::UPropertyView& property,
            size_t expectedSize,
            uint64_t& out)
        {
            out = 0;

            RuntimeReflection::ParamRange range;
            if (RuntimeReflection::ReadResult result =
                    RuntimeReflection::TryGetParameterRange(reader,
                                                            params,
                                                            parmsSize,
                                                            property,
                                                            expectedSize,
                                                            range);
                !result)
            {
                // Redacted object correlates are private best-effort hints; unreadable
                // bytes mean "no token", not a copied-params failure.
                if (result.Status == RuntimeReflection::ReadStatus::Unreadable)
                    return RuntimeReflection::ReadResult::Ok();
                return result;
            }
            if (range.Size != sizeof(uintptr_t) || expectedSize != sizeof(uintptr_t))
            {
                return RuntimeReflection::ReadResult::Fail(
                    RuntimeReflection::ReadStatus::Implausible,
                    "redacted object correlate has unexpected size");
            }

            uintptr_t objectAddress = 0;
            std::memcpy(&objectAddress, range.Data, sizeof(objectAddress));
            if (objectAddress == 0)
                return RuntimeReflection::ReadResult::Ok();
            if (!IsCanonicalUserPointer(objectAddress))
            {
                return RuntimeReflection::ReadResult::Fail(
                    RuntimeReflection::ReadStatus::Implausible,
                    "redacted object correlate pointer is implausible");
            }

            out = AssignProcessLocalSubjectToken(objectAddress);
            if (out == 0)
            {
                return RuntimeReflection::ReadResult::Fail(
                    RuntimeReflection::ReadStatus::OutOfBounds,
                    "redacted object correlate token space exhausted");
            }
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult TryValidateProcessLocalSubjectTokenCandidate(
            const RuntimeReflection::MemoryReader& reader,
            const void* params,
            uint16_t parmsSize,
            const RuntimeReflection::UPropertyView& property,
            size_t expectedSize,
            uint64_t& out)
        {
            out = 0;

            RuntimeReflection::ParamRange range;
            if (RuntimeReflection::ReadResult result =
                    RuntimeReflection::TryGetParameterRange(reader,
                                                            params,
                                                            parmsSize,
                                                            property,
                                                            expectedSize,
                                                            range);
                !result)
            {
                if (result.Status == RuntimeReflection::ReadStatus::Unreadable)
                    return RuntimeReflection::ReadResult::Ok();
                return result;
            }
            if (range.Size != sizeof(uintptr_t) || expectedSize != sizeof(uintptr_t))
            {
                return RuntimeReflection::ReadResult::Fail(
                    RuntimeReflection::ReadStatus::Implausible,
                    "redacted object correlate has unexpected size");
            }

            uintptr_t objectAddress = 0;
            std::memcpy(&objectAddress, range.Data, sizeof(objectAddress));
            if (objectAddress == 0)
                return RuntimeReflection::ReadResult::Ok();
            if (!IsCanonicalUserPointer(objectAddress))
            {
                return RuntimeReflection::ReadResult::Fail(
                    RuntimeReflection::ReadStatus::Implausible,
                    "redacted object correlate pointer is implausible");
            }

            out = std::numeric_limits<uint64_t>::max();
            return RuntimeReflection::ReadResult::Ok();
        }

        std::string BuildFunctionShapeMismatchReason(const RuntimeReflection::UFunctionView& function,
                                                     const LifecycleFunctionSpec& spec,
                                                     std::string_view cause)
        {
            std::string reason = "lifecycle_function_shape_mismatch";
            reason += "_cause_";
            reason += SafeDiagnosticReasonToken(cause);
            AppendObservedPropertyFNameChain(reason, function);
            AppendKeyValueUnsigned(reason, "expected_function_flags", spec.FunctionFlags);
            AppendKeyValueUnsigned(reason, "observed_function_flags", function.FunctionFlags);
            AppendKeyValueUnsigned(reason, "expected_num_parms", spec.NumParms);
            AppendKeyValueUnsigned(reason, "observed_num_parms", function.NumParms);
            AppendKeyValueUnsigned(reason, "expected_parms_size", spec.ParmsSize);
            AppendKeyValueUnsigned(reason, "observed_parms_size", function.ParmsSize);
            AppendKeyValueUnsigned(reason, "expected_return_value_offset", spec.ReturnValueOffset);
            AppendKeyValueUnsigned(reason, "observed_return_value_offset", function.ReturnValueOffset);
            AppendKeyValueUnsigned(reason, "expected_property_count", spec.FieldCount);
            AppendKeyValueUnsigned(reason, "observed_property_count", function.Parameters.size());
            return BoundDiagnosticReason(std::move(reason));
        }

        std::string BuildPropertyFNameMismatchReason(
            const RuntimeReflection::MemoryReader& reader,
            const RuntimeReflection::FieldLayout& layout,
            const RuntimeReflection::UFunctionView& function,
            const LifecycleFunctionSpec& spec,
            int32_t expectedNameIndex,
            std::string_view cause,
            size_t position)
        {
            std::string reason = "lifecycle_property_FName_mismatch_expected_";
            reason += "name_index_";
            reason += std::to_string(expectedNameIndex);
            const std::string safeCause = SafeDiagnosticReasonToken(cause);
            AppendKeyValue(reason, "cause", safeCause);
            if (position != std::numeric_limits<size_t>::max())
                AppendKeyValueUnsigned(reason, "position", position);
            AppendKeyValueUnsigned(reason, "observed_count", function.Parameters.size());
            AppendObservedPropertyFNameChain(reason, function);
            const int32_t observedNameIndex =
                position < function.Parameters.size()
                    ? function.Parameters[position].Object.NamePrivate.ComparisonIndex
                    : -1;
            AppendCurrentRuntimeUnapprovedDriftDiagnostic(reason,
                                                          spec,
                                                          function,
                                                          position,
                                                          expectedNameIndex,
                                                          observedNameIndex);
            for (size_t index = 0; index < function.Parameters.size(); ++index)
            {
                AppendObservedPropertyMetadata(reader, layout, function.Parameters[index], index, reason);
            }
            return BoundDiagnosticReason(std::move(reason));
        }

        bool HasEarlierPropertyNameIndex(const RuntimeReflection::UFunctionView& function,
                                         size_t position,
                                         int32_t observedNameIndex)
        {
            for (size_t index = 0; index < position; ++index)
            {
                if (function.Parameters[index].Object.NamePrivate.ComparisonIndex == observedNameIndex)
                    return true;
            }
            return false;
        }

        bool MatchesDifferentExpectedPropertyName(const LifecycleFunctionSpec& spec,
                                                  size_t position,
                                                  int32_t observedNameIndex)
        {
            for (size_t index = 0; index < spec.FieldCount; ++index)
            {
                if (index != position && spec.Fields[index].NameIndex == observedNameIndex)
                    return true;
            }
            return false;
        }

        bool AllowsPropertyFNameDrift(LifecycleFunction function)
        {
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

        bool IsApprovedObservedPropertyFNameDrift(LifecycleFunction function,
                                                  size_t position,
                                                  int32_t observedNameIndex)
        {
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

        bool MatchesApprovedPropertyFNameDriftChain(
            LifecycleFunction function,
            const RuntimeReflection::UFunctionView& reflectedFunction)
        {
            switch (function)
            {
            case LifecycleFunction::HandleNewPlayer:
                if (reflectedFunction.Parameters.size() != kObservedHandleNewPlayerDriftChains[0].size())
                    return false;
                for (const auto& chain : kObservedHandleNewPlayerDriftChains)
                {
                    bool matches = true;
                    for (size_t index = 0; index < chain.size(); ++index)
                    {
                        if (reflectedFunction.Parameters[index].Object.NamePrivate.ComparisonIndex !=
                            chain[index])
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
                return reflectedFunction.Parameters.size() == 1 &&
                    (reflectedFunction.Parameters[0].Object.NamePrivate.ComparisonIndex ==
                         kObservedOnLogoutName0 ||
                     reflectedFunction.Parameters[0].Object.NamePrivate.ComparisonIndex ==
                         kObservedOnLogoutPostRestartName0 ||
                     reflectedFunction.Parameters[0].Object.NamePrivate.ComparisonIndex ==
                         kObservedOnLogoutRagnarokRestart20260606Name0 ||
                     reflectedFunction.Parameters[0].Object.NamePrivate.ComparisonIndex ==
                        kObservedOnLogoutCurrentRuntime20260607Name0);
            case LifecycleFunction::CheckJoinInProgressDiagnostic:
                if (reflectedFunction.Parameters.size() != kObservedCheckJoinInProgressDriftChains[0].size())
                    return false;
                for (const auto& chain : kObservedCheckJoinInProgressDriftChains)
                {
                    bool matches = true;
                    for (size_t index = 0; index < chain.size(); ++index)
                    {
                        if (reflectedFunction.Parameters[index].Object.NamePrivate.ComparisonIndex !=
                            chain[index])
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

        std::string BuildPropertyFNameDriftReason(const LifecycleInvocation& invocation)
        {
            if (invocation.PropertyFNameDrifts.empty())
                return {};

            const LifecyclePropertyFNameDrift& first = invocation.PropertyFNameDrifts[0];
            std::string reason = "lifecycle_property_FName_drift";
            AppendKeyValueSigned(reason, "expected_name_index", first.ExpectedNameIndex);
            AppendKeyValueSigned(reason, "observed_name_index", first.ObservedNameIndex);
            AppendKeyValueSigned(reason, "function_name_index", invocation.FunctionNameIndex);
            AppendKeyValueSigned(reason, "outer_name_index", invocation.OuterNameIndex);
            AppendKeyValueUnsigned(reason, "drift_count", invocation.PropertyFNameDrifts.size());
            AppendObservedPropertyFNameChain(reason, invocation);

            for (size_t index = 0; index < invocation.PropertyFNameDrifts.size(); ++index)
            {
                const LifecyclePropertyFNameDrift& drift = invocation.PropertyFNameDrifts[index];
                const std::string prefix = "drift_" + std::to_string(index);
                AppendKeyValueUnsigned(reason, prefix + "_position", drift.Position);
                AppendKeyValueSigned(reason, prefix + "_expected_name_index", drift.ExpectedNameIndex);
                AppendKeyValueSigned(reason, prefix + "_observed_name_index", drift.ObservedNameIndex);
                AppendKeyValueSigned(reason,
                                     prefix + "_delta",
                                     static_cast<int64_t>(drift.ObservedNameIndex) -
                                         static_cast<int64_t>(drift.ExpectedNameIndex));
            }

            return BoundDiagnosticReason(std::move(reason));
        }
    }

    void ResetProcessLocalSubjectTokensForTesting()
    {
        auto& state = GetProcessLocalSubjectTokenState();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.NextToken = 1;
        state.TokensByObjectFingerprint.clear();
    }

    void SetNextProcessLocalSubjectTokenForTesting(uint64_t nextToken)
    {
        auto& state = GetProcessLocalSubjectTokenState();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.NextToken = nextToken;
    }

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out)
    {
        return TryIdentifyLifecycleInvocation(reader,
                                              options,
                                              function,
                                              params,
                                              out,
                                              ProcessLocalSubjectTokenMode::Assign);
    }

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out,
        ProcessLocalSubjectTokenMode tokenMode)
    {
        out = {};

        if (RuntimeReflection::ReadResult gate = ValidateGate(options); !gate)
            return SafeDiagnosticFailure(gate);
        if (!function)
            return SafeDiagnosticFailure(RuntimeReflection::ReadStatus::InvalidArgument,
                                         "null UFunction pointer");

        RuntimeReflection::UObjectView functionObject;
        if (RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, *options.Layout, function, functionObject);
            !result)
        {
            return SafeDiagnosticFailure(result);
        }

        const LifecycleFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return SafeDiagnosticFailure(RuntimeReflection::ReadStatus::Implausible,
                                         "UFunction FName index is not a supported lifecycle target");

        RuntimeReflection::UFunctionView reflectedFunction;
        if (RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUFunction(reader, options, function, reflectedFunction);
            !result)
        {
            return SafeDiagnosticFailure(result);
        }
        if (RuntimeReflection::ReadResult result =
                ValidateFunctionClass(reader, *options.Layout, reflectedFunction);
            !result)
        {
            return SafeDiagnosticFailure(result);
        }
        if (RuntimeReflection::ReadResult result = ValidateFunctionShape(reflectedFunction, *spec); !result)
        {
            return RuntimeReflection::ReadResult::Fail(
                result.Status,
                BuildFunctionShapeMismatchReason(reflectedFunction, *spec, result.Reason));
        }
        if (RuntimeReflection::ReadResult result =
                ValidateFunctionOuter(reader, *options.Layout, reflectedFunction, *spec);
            !result)
        {
            return SafeDiagnosticFailure(result);
        }

        LifecycleInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges =
            params != nullptr && tokenMode != ProcessLocalSubjectTokenMode::MetadataOnly;
        value.PropertyNameIndicesMatched = true;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "lifecycle field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);
        value.PropertyFNameDrifts.reserve(spec->FieldCount);
        const bool allowPropertyFNameDrift = AllowsPropertyFNameDrift(spec->Function);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const LifecycleFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (property.Object.NamePrivate.Number != 0)
            {
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           BuildPropertyFNameMismatchReason(reader,
                                                                                            *options.Layout,
                                                                                            reflectedFunction,
                                                                                            *spec,
                                                                                            fieldSpec.NameIndex,
                                                                                            "property_FName_number_mismatch",
                                                                                            i));
            }
            if (HasEarlierPropertyNameIndex(reflectedFunction,
                                            i,
                                            property.Object.NamePrivate.ComparisonIndex))
            {
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           BuildPropertyFNameMismatchReason(reader,
                                                                                            *options.Layout,
                                                                                            reflectedFunction,
                                                                                            *spec,
                                                                                            fieldSpec.NameIndex,
                                                                                            "duplicate_observed_property_FName",
                                                                                            i));
            }
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec, !allowPropertyFNameDrift);
                !result)
            {
                return RuntimeReflection::ReadResult::Fail(
                    result.Status,
                    BuildPropertyValidationMismatchReason(reader,
                                                          *options.Layout,
                                                          reflectedFunction,
                                                          *spec,
                                                          property,
                                                          i,
                                                          fieldSpec,
                                                          result.Reason));
            }
            if (allowPropertyFNameDrift &&
                property.Object.NamePrivate.ComparisonIndex != fieldSpec.NameIndex &&
                MatchesDifferentExpectedPropertyName(*spec, i, property.Object.NamePrivate.ComparisonIndex))
            {
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           BuildPropertyFNameMismatchReason(reader,
                                                                                            *options.Layout,
                                                                                            reflectedFunction,
                                                                                            *spec,
                                                                                            fieldSpec.NameIndex,
                                                                                            "observed_property_FName_matches_different_expected_property",
                                                                                            i));
            }
            if (property.Object.NamePrivate.ComparisonIndex != fieldSpec.NameIndex)
            {
                if (!allowPropertyFNameDrift ||
                    !IsApprovedObservedPropertyFNameDrift(
                        spec->Function,
                        i,
                        property.Object.NamePrivate.ComparisonIndex))
                {
                    return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                               BuildPropertyFNameMismatchReason(reader,
                                                                                                *options.Layout,
                                                                                                reflectedFunction,
                                                                                                *spec,
                                                                                                fieldSpec.NameIndex,
                                                                                                "unapproved_observed_property_FName",
                                                                                                i));
                }

                value.PropertyNameIndicesMatched = false;
                value.PropertyFNameDriftDiagnosticOnly = true;
                value.PropertyFNameDrifts.push_back({
                    i,
                    fieldSpec.Field,
                    fieldSpec.NameIndex,
                    property.Object.NamePrivate.ComparisonIndex,
                });
            }
        }

        if (!value.PropertyNameIndicesMatched &&
            (value.PropertyFNameDrifts.size() != spec->FieldCount ||
             !MatchesApprovedPropertyFNameDriftChain(spec->Function, reflectedFunction)))
        {
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       BuildPropertyFNameMismatchReason(reader,
                                                                                        *options.Layout,
                                                                                        reflectedFunction,
                                                                                        *spec,
                                                                                        spec->Fields[0].NameIndex,
                                                                                        "unapproved_observed_property_FName_drift_chain",
                                                                                        0));
        }

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const LifecycleFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];

            LifecycleFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = property.Object.NamePrivate.ComparisonIndex;
            field.Offset = fieldSpec.Offset;
            field.Size = fieldSpec.Size;
            field.ExposesRange = fieldSpec.ExposesRange;
            field.Redacted = fieldSpec.Redacted;

            if (value.HasParameterRanges && field.ExposesRange)
            {
                RuntimeReflection::ParamRange range;
                if (RuntimeReflection::ReadResult result =
                        RuntimeReflection::TryGetParameterRange(reader,
                                                                params,
                                                                reflectedFunction.ParmsSize,
                                                                property,
                                                                fieldSpec.Size,
                                                                range);
                    !result)
                {
                    return SafeDiagnosticFailure(result);
                }
                if (RuntimeReflection::ReadResult result =
                        CopyCanonicalBool(range, field.CopiedBoolValue);
                    !result)
                {
                    return SafeDiagnosticFailure(result);
                }
                field.HasCopiedBoolValue = true;
            }
            else if (value.HasParameterRanges &&
                     field.Redacted &&
                     fieldSpec.ClassNameIndex == kObjectPropertyClassNameIndex &&
                     UsesProcessLocalSubjectToken(spec->Function, fieldSpec.Field) &&
                     tokenMode != ProcessLocalSubjectTokenMode::Skip)
            {
                const RuntimeReflection::ReadResult result =
                    tokenMode == ProcessLocalSubjectTokenMode::Assign
                        ? TryAssignProcessLocalSubjectToken(reader,
                                                            params,
                                                            reflectedFunction.ParmsSize,
                                                            property,
                                                            fieldSpec.Size,
                                                            field.ProcessLocalSubjectToken)
                        : TryValidateProcessLocalSubjectTokenCandidate(reader,
                                                                       params,
                                                                       reflectedFunction.ParmsSize,
                                                                       property,
                                                                       fieldSpec.Size,
                                                                       field.ProcessLocalSubjectToken);
                if (!result)
                {
                    return SafeDiagnosticFailure(result);
                }
            }

            value.Fields.push_back(field);
        }

        std::string okReason;
        if (!value.PropertyNameIndicesMatched)
            okReason = BuildPropertyFNameDriftReason(value);

        out = std::move(value);
        if (!okReason.empty())
            return {RuntimeReflection::ReadStatus::Ok, std::move(okReason)};
        return RuntimeReflection::ReadResult::Ok();
    }
}
