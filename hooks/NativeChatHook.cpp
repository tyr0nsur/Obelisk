#include "NativeChatHook.h"
#include "StartupNativeHook.h"
#include "core/CommandDispatcher.h"
#include "core/PlayerLifecycleDispatcher.h"
#include "runtime/BinaryIdentity.h"
#include "runtime/Logger.h"
#include "ue/Memory.h"
#include "ue/NativeChatText.h"
#include "ue/ObjectClassValidation.h"
#include "ue/SafeMemoryRead.h"
#include "extern/nlohmann/json.hpp"

#include <array>
#include <atomic>
#include <chrono>
#include <cstring>
#include <string_view>
#include <vector>
#include <utility>
#include <sys/syscall.h>
#include <unistd.h>

namespace Obelisk::Hooks::NativeChatHook
{
    namespace
    {
        using UE::NativeChatText::FString;
        struct LinearColor { float R, G, B, A; };
        static_assert(sizeof(LinearColor) == 16);
        using Receive = void (*)(void*, const FString*, uint8_t);
        using Reply = void (*)(void*, const FString*, LinearColor, bool);
        using UniqueId = void (*)(FString* output, void* playerState);
        using Free = void (*)(void* allocation);

        constexpr char kBinarySha[] =
            "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520";
        constexpr uintptr_t kElfImageBase = 0x400000;
        constexpr uintptr_t kReceiveAddress = 0xf76840;
        constexpr uintptr_t kReplyAddress = 0x136ed90;
        constexpr uintptr_t kUniqueIdAddress = 0xfcf060;
        constexpr uintptr_t kFreeAddress = 0x1af8e30;
        constexpr std::array<uint8_t, 20> kReceivePrologue = {
            0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,
            0x41,0x54,0x53,0x48,0x81,0xec,0x28,0x02,0x00,0x00
        };
        constexpr std::array<uint8_t, 32> kReceiveSignature = {
            0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,
            0x41,0x54,0x53,0x48,0x81,0xec,0x28,0x02,0x00,0x00,
            0x89,0x95,0x24,0xfe,0xff,0xff,0x49,0x89,0xf4,0x49,0x89,0xfd
        };
        constexpr std::array<uint8_t, 32> kReplyPrologue = {
            0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,0x41,0x55,0x41,0x54,
            0x53,0x48,0x83,0xec,0x48,0x41,0x89,0xd7,0x48,0x89,0xf3,0x49,
            0x89,0xfc,0x0f,0x57,0xd2,0x0f,0x29,0x55
        };
        constexpr std::array<uint8_t, 7> kReplyFNameBinding = {
            0x48,0x8b,0x35,0xd1,0xbd,0x57,0x04
        };

        // Bounded owner/layout proofs independently checked against this exact
        // ELF in lifecycle-public-owner-audit.json. These are rechecked in the
        // mapped image before advertising the player/lifecycle backend.
        struct ProfileProof { uintptr_t Address; std::string_view Bytes; };
        constexpr std::array<ProfileProof, 51> kLifecycleProfileProofs{{
            {0x13ccda4, "48 8b 05 25 5e 52 04"}, // GetStaticClass-like getter loads ShooterGameMode global
            {0x13ccdb0, "be 24 0b 0e 04 ba d0 2b 8f 05"}, // Getter binds UTF32 ShooterGameMode name and class global
            {0x19c0031, "e8 6a cd a0 ff"}, // Class metadata invokes that getter
            {0x19c0036, "48 89 05 c3 f1 f3 03"}, // Class metadata stores returned class in alias 0x58ff200
            {0x2e2761c, "48 8b 3d 85 14 b8 02"}, // GameMode metadata reads canonical class global
            {0x2e2762d, "be 1c 51 56 04 ba a8 8a 9a 05"}, // GameMode metadata binds UTF32 name and canonical class global
            {0x2e27648, "48 89 3d c9 c7 b8 02"}, // GameMode metadata stores class result in alias 0x59b3e18
            {0x1d50bdd, "49 89 f5"}, // UObject allocator saves incoming RSI outer as R13
            {0x1d50d9b, "4c 89 ad 40 ff ff ff"}, // Saves that same R13 outer on stack
            {0x1d50e5c, "48 8b 85 40 ff ff ff"}, // Loads saved outer into RAX
            {0x1d50e63, "49 89 44 24 20"}, // Stores incoming outer in allocated UObject +0x20
            {0x1cd633c, "49 8b 5d 20"}, // UFunction Invoke reads owner from OuterPrivate +0x20
            {0x1d47f5d, "48 89 43 20"}, // UObject constructor stores OuterPrivate +0x20
            {0x1d4b2c0, "48 8b 4f 10"}, // Native IsA reads UObject.ClassPrivate +0x10
            {0x1d4b2d0, "48 8b 49 30"}, // Native IsA traverses SuperStruct +0x30
            {0x1cd60ce, "4d 89 cd"}, // UFunction constructor preserves R9 storage size in R13
            {0x1cd6107, "44 89 6b 40"}, // Constructor stores storage size in PropertiesSize +0x40, not ParmsSize
            {0x1cd6180, "c6 87 96 00 00 00 00"}, // Bind initializes NumParms byte +0x96
            {0x1cd6187, "c7 87 98 00 00 00 00 00 ff ff"}, // Bind initializes ParmsSize=0 and ReturnValueOffset=0xffff
            {0x1cd61cc, "44 88 87 96 00 00 00"}, // Bind records count of CPF_Parm properties
            {0x1cd61d3, "8b 48 34 8b 70 4c 0f af 48 30 01 f1"}, // Bind computes OffsetInternal + ElementSize * ArrayDim
            {0x1cd61df, "66 89 8f 98 00 00 00"}, // Bind writes computed logical parameter end to ParmsSize +0x98
            {0x1cd61eb, "66 89 b7 9a 00 00 00"}, // Bind writes return property offset to +0x9a
            {0x19daa6e, "e8 8d 55 fe ff"}, // Function metadata obtains ShooterGameMode class from metadata root
            {0x19daa73, "48 89 c3"}, // Preserves returned declaring class in RBX
            {0x19daaba, "48 89 de"}, // Passes declaring class as RSI outer to UObject allocator
            {0x19daac0, "e8 fb 60 37 00"}, // Creates UFunction through verified UObject allocator
            {0x19daae4, "41 b9 20 00 00 00"}, // Passes 32 bytes storage size to UFunction constructor
            {0x13ccfb2, "48 89 75 d0"}, // Wrapper stores controller at first parameter
            {0x13ccfbe, "44 88 45 e8"}, // Wrapper stores bIsFromLogin at parameter +24
            {0x13ccfe5, "8a 45 e9"}, // Wrapper reads returned bool from parameter +25
            {0x19dabb5, "41 b8 80 05 00 00"}, // Return bool metadata flags include CPF_Parm and CPF_ReturnParm
            {0x19dac7f, "41 b8 80 00 00 00"}, // Login bool metadata marks CPF_Parm without CPF_ReturnParm
            {0x19ddd4e, "e8 ad 22 fe ff"}, // Function metadata obtains ShooterGameMode class from metadata root
            {0x19ddd9a, "48 89 de"}, // Passes returned declaring class as RSI outer
            {0x19ddda0, "e8 1b 2e 37 00"}, // Creates UFunction through verified UObject allocator
            {0x2e2947e, "e8 6d e1 ff ff"}, // Function metadata obtains GameMode class from metadata root
            {0x2e294ca, "48 89 de"}, // Passes returned declaring class as RSI outer
            {0x2e294d0, "e8 eb 76 f2 fe"}, // Creates UFunction through verified UObject allocator
            {0x2e295b2, "31 c9"}, // NewPlayer reflected field offset is zero
            {0x2e295bc, "41 c7 46 34 08 00 00 00"}, // NewPlayer field ElementSize is eight bytes
            {0xf5b86b, "48 83 bb 88 04 00 00 00"}, // Authority path requires non-null Controller.PlayerState +0x488
            {0xf5b881, "4c 8b b0 50 02 00 00"}, // Obtains game mode from world +0x250
            {0xf5b88d, "4c 89 f7 48 89 de"}, // Sets RDI=GameMode and RSI=Controller before named OnLogout wrapper
            {0xf5b893, "e8 e8 17 47 00"}, // Calls OnLogout wrapper 0x13cd080
            {0xf5b89e, "e8 2d c7 f3 ff"}, // Only afterward calls native GameMode logout path 0xe97fd0
            {0x26318fe, "49 c7 04 24 60 f6 42 04"}, // Native GameMode constructor installs vtable 0x442f660
            {0x4430228, "f0 91 d3 02 00 00 00 00"}, // Native GameMode vtable slot +0xbc8 points to named K2_PostLogin wrapper
            {0x2632882, "48 8b 80 c8 0b 00 00"}, // GameMode path loads virtual K2_PostLogin slot +0xbc8
            {0x2632889, "4c 89 ef 4c 89 f6"}, // Sets RDI=GameMode and RSI=NewPlayer before event
            {0x263288f, "ff d0"}, // Calls virtual K2_PostLogin wrapper
        }};

        bool ValidateMappedLifecycleProfile(uintptr_t imageBase) noexcept
        {
            for (const auto& proof : kLifecycleProfileProofs)
            {
                const auto offset = proof.Address - kElfImageBase;
                if (proof.Address < kElfImageBase || imageBase > UINTPTR_MAX - offset)
                    return false;
                std::array<uint8_t, 32> expected{};
                std::array<uint8_t, 32> actual{};
                size_t length = 0;
                const auto nibble = [](char value) -> int {
                    if (value >= '0' && value <= '9') return value - '0';
                    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
                    return -1;
                };
                for (size_t i = 0; i < proof.Bytes.size(); i += 3)
                {
                    if (i + 1 >= proof.Bytes.size() || length == expected.size() ||
                        (i + 2 < proof.Bytes.size() && proof.Bytes[i + 2] != ' '))
                        return false;
                    const int high = nibble(proof.Bytes[i]);
                    const int low = nibble(proof.Bytes[i + 1]);
                    if (high < 0 || low < 0)
                        return false;
                    expected[length++] = static_cast<uint8_t>((high << 4) | low);
                }
                if (!length || !Memory::ReadExact(actual.data(),
                        reinterpret_cast<const void*>(imageBase + offset), length) ||
                    std::memcmp(actual.data(), expected.data(), length) != 0)
                    return false;
            }
            return true;
        }

        struct State
        {
            StartupNativeHook Hook;
            Receive Original = nullptr;
            Reply Send = nullptr;
            UniqueId GetUniqueId = nullptr;
            Free FreeString = nullptr;
            uintptr_t ImageBase = 0;
            std::atomic<bool> Installed{false};
            std::atomic<uint64_t> CommandCount{0};
            std::atomic<uint64_t> LifecycleCount{0};
            uint64_t LifecycleProcessEpoch = 0;
        };
        State& GetState()
        {
            // The hook and trampoline live until process exit; no hot unload.
            static auto* state = new State();
            return *state;
        }

        // Offsets bound to metadata in the current, hash-verified executable.
        constexpr uintptr_t kNetConnectionOffset = 0x668;
        constexpr uintptr_t kPlayerStateOffset = 0x488;
        constexpr uintptr_t kPlayerNameOffset = 0x478;
        constexpr uintptr_t kShooterPlayerControllerClassGlobal = 0x58eebf0;
        constexpr uintptr_t kShooterPlayerStateClassGlobal = 0x58eeb80;
        constexpr uintptr_t kShooterGameModeClassGlobal = 0x58f2bd0;
        constexpr uintptr_t kGameModeClassGlobal = 0x59a8aa8;
        struct ReplyContext
        {
            void* Controller;
            void* Connection;
        };
        bool ReadPointer(void* object, uintptr_t offset, void*& result)
        {
            const auto address = reinterpret_cast<uintptr_t>(object);
            result = nullptr;
            return object && address <= UINTPTR_MAX - offset &&
                   Memory::ReadExact(&result, reinterpret_cast<const void*>(address + offset), sizeof(result));
        }
        const void* ProfileAddress(uintptr_t address) noexcept
        {
            const auto imageBase = GetState().ImageBase;
            if (!imageBase || address < kElfImageBase)
                return nullptr;
            const auto offset = address - kElfImageBase;
            if (imageBase > UINTPTR_MAX - offset)
                return nullptr;
            return reinterpret_cast<const void*>(imageBase + offset);
        }
        bool ReadProfileClass(uintptr_t classGlobal, void*& expectedClass) noexcept
        {
            expectedClass = nullptr;
            return Memory::ReadExact(&expectedClass, ProfileAddress(classGlobal), sizeof(expectedClass)) && expectedClass;
        }
        bool IsInstanceOfProfileClass(void* object, uintptr_t classGlobal)
        {
            void* expectedClass = nullptr;
            if (!object || !ReadProfileClass(classGlobal, expectedClass))
                return false;
            return UE::ObjectClassValidation::HasClassInAncestry(object, expectedClass);
        }
        template<class Value>
        bool ReadField(const void* object, uintptr_t offset, Value& result) noexcept
        {
            const auto address = reinterpret_cast<uintptr_t>(object);
            return object && address <= UINTPTR_MAX - offset &&
                Memory::ReadExact(&result, reinterpret_cast<const void*>(address + offset), sizeof(result));
        }
        bool IsMainThread() noexcept
        {
            static thread_local const bool isMain = syscall(SYS_gettid) == getpid();
            return isMain;
        }
        struct PlayerObservation
        {
            std::string PlayerName;
            std::string PlatformId;
            uint64_t IdentityFlags = 0;
            bool PlayerStateAvailable = false;
            bool NetConnectionAvailable = false;
            bool ControllerClassValidated = false;
            bool PlayerStateClassValidated = false;
            bool MainThread = false;
        };
        PlayerObservation CapturePlayer(void* controller)
        {
            PlayerObservation copied;
            void* playerState = nullptr;
            void* connection = nullptr;
            copied.MainThread = IsMainThread();
            copied.ControllerClassValidated =
                IsInstanceOfProfileClass(controller, kShooterPlayerControllerClassGlobal);
            if (copied.ControllerClassValidated)
            {
                ReadPointer(controller, kNetConnectionOffset, connection);
                if (ReadPointer(controller, kPlayerStateOffset, playerState) && playerState)
                    copied.PlayerStateClassValidated = IsInstanceOfProfileClass(playerState, kShooterPlayerStateClassGlobal);
            }
            copied.PlayerStateAvailable = playerState != nullptr;
            copied.NetConnectionAvailable = connection != nullptr;
            if (copied.PlayerStateClassValidated)
            {
                const auto address = reinterpret_cast<uintptr_t>(playerState);
                if (address <= UINTPTR_MAX - kPlayerNameOffset)
                    UE::NativeChatText::Decode(reinterpret_cast<const FString*>(address + kPlayerNameOffset), copied.PlayerName);
                auto& state = GetState();
                if (copied.MainThread && state.GetUniqueId && state.FreeString)
                {
                    FString output{};
                    state.GetUniqueId(&output, playerState);
                    UE::NativeChatText::Decode(&output, copied.PlatformId);
                    if (output.Data)
                        state.FreeString(const_cast<char32_t*>(output.Data));
                }
            }
            // Decode establishes UTF-8 and rejects embedded NUL. Bounds are the
            // public snapshot contract; logs use these same pre-callback copies.
            if (copied.PlayerName.size() > OBELISK_COMMAND_PLAYER_NAME_MAX_BYTES)
                copied.PlayerName.clear();
            if (copied.PlatformId.size() > OBELISK_COMMAND_PLAYER_PLATFORM_ID_MAX_BYTES)
                copied.PlatformId.clear();
            if (!copied.PlayerName.empty())
                copied.IdentityFlags |= OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE;
            if (!copied.PlatformId.empty())
                copied.IdentityFlags |= OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE;
            return copied;
        }
        nlohmann::json PlayerDetails(const PlayerObservation& copied)
        {
            // JSON escapes control characters; names cannot inject log lines.
            return {
                {"player_name", copied.PlayerName}, {"platform_id", copied.PlatformId},
                {"player_state_available", copied.PlayerStateAvailable},
                {"net_connection_available", copied.NetConnectionAvailable},
                {"controller_class_validated", copied.ControllerClassValidated},
                {"player_state_class_validated", copied.PlayerStateClassValidated},
                {"main_thread", copied.MainThread},
                {"identity_scope", "copied native controller observation at callback entry"}
            };
        }

        bool ValidateFunctionOwner(void* object, void* function, uintptr_t declarationGlobal) noexcept
        {
            void* callerClass = nullptr;
            void* owner = nullptr;
            void* shooterGameMode = nullptr;
            void* declarationBase = nullptr;
            if (!ReadPointer(object, 0x10, callerClass) || !callerClass ||
                !ReadPointer(function, 0x20, owner) || !owner ||
                !ReadProfileClass(kShooterGameModeClassGlobal, shooterGameMode) ||
                !ReadProfileClass(declarationGlobal, declarationBase))
                return false;
            // Outer is a UClass, so follow its own SuperStruct instead of its
            // UObject.ClassPrivate metaclass. The owner must belong to this
            // actor and be at or below the verified native declaration base.
            return UE::ObjectClassValidation::ClassHasAncestor(callerClass, shooterGameMode) &&
                UE::ObjectClassValidation::ClassHasAncestor(callerClass, owner) &&
                UE::ObjectClassValidation::ClassHasAncestor(owner, declarationBase);
        }

        const char* LifecycleName(PlayerLifecycleFrame::Event selected) noexcept
        {
            switch (selected)
            {
                case PlayerLifecycleFrame::Event::HandleNewPlayer: return "HandleNewPlayer";
                case PlayerLifecycleFrame::Event::PostLogin: return "K2_PostLogin";
                case PlayerLifecycleFrame::Event::Logout: return "OnLogout";
                default: return "none";
            }
        }

        nlohmann::json LifecycleDetails(const PlayerLifecycleFrame& frame, const char* phase)
        {
            const auto has = [&](uint64_t flag) { return (frame.Flags & flag) != 0; };
            nlohmann::json details{
                {"event", LifecycleName(frame.Selected)}, {"phase", phase},
                {"observation_only", true}, {"owner_class_validated", true},
                {"controller_class_validated", has(OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED)},
                {"main_thread", has(OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD)},
                {"net_connection_available", has(OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE)},
                {"player_state_available", frame.PlayerStateAvailable},
                {"player_state_class_validated", frame.PlayerStateClassValidated},
                {"player_name", frame.PlayerName}, {"platform_id", frame.PlatformId},
                {"parameter_bytes", frame.ParameterBytes}, {"num_parms", frame.NumParms},
                {"return_value_offset", frame.ReturnValueOffset},
                {"identity_scope", "owned copies captured at notification entry"},
                {"process_epoch", frame.ProcessEpoch}
            };
            if (frame.Selected == PlayerLifecycleFrame::Event::HandleNewPlayer)
            {
                details["from_login_value"] = frame.FromLoginValue;
                details["from_login_canonical"] = frame.FromLoginValue <= 1;
                if (frame.FromLoginValue <= 1)
                {
                    details["is_from_login"] = frame.FromLoginValue == 1;
                    details["handler_context"] = frame.FromLoginValue ? "login_handler" : "non_login_handler";
                }
            }
            if (frame.Sequence)
                details["sequence"] = frame.Sequence;
            return details;
        }

        void EmitLifecycle(PlayerLifecycleFrame& frame, uint32_t kind) noexcept
        {
            auto& state = GetState();
            auto previous = state.LifecycleCount.load(std::memory_order_relaxed);
            while (previous != UINT64_MAX && !state.LifecycleCount.compare_exchange_weak(
                    previous, previous + 1, std::memory_order_relaxed)) {}
            if (previous == UINT64_MAX)
                return; // Never wrap/reuse an observation sequence.
            frame.Sequence = previous + 1;
            const Core::PlayerLifecycleSnapshot snapshot{
                kind, frame.Flags, frame.Sequence, frame.ProcessEpoch, frame.PlayerName, frame.PlatformId};
            Core::PlayerLifecycleDispatcher::Get().Dispatch(snapshot);
        }

        bool ReplyToOrigin(void* controller, std::string_view message, void* data) noexcept
        {
            bool dispatched = false;
            try
            {
                auto& state = GetState();
                const auto* context = static_cast<const ReplyContext*>(data);
                void* connection = nullptr;
                if (!state.Installed.load(std::memory_order_acquire) || !controller || !state.Send ||
                    !IsMainThread() || !context || controller != context->Controller || !context->Connection ||
                    !IsInstanceOfProfileClass(controller, kShooterPlayerControllerClassGlobal) ||
                    !ReadPointer(controller, kNetConnectionOffset, connection) || connection != context->Connection)
                    return false;
                std::vector<char32_t> text;
                if (!UE::NativeChatText::Encode(message, text))
                    return false;
                const FString payload{text.data(), static_cast<int32_t>(text.size()),
                                      static_cast<int32_t>(text.size())};
                // The RPC wrapper copies the borrowed UTF-32 FString, creates its
                // UFunction parameters and routes through this actor's ProcessEvent.
                state.Send(controller, &payload, LinearColor{1, 1, 1, 1}, false);
                dispatched = true;
                OBELISK_INFO("Native command directed reply dispatched. utf8_bytes={}", message.size());
                return true; // Dispatch observed; client delivery is tested separately.
            }
            catch (...)
            {
                return dispatched;
            }
        }

        void ReceiveDetour(void* controller, const FString* message, uint8_t mode)
        {
            auto& state = GetState();
            bool handled = false;
            try
            {
                if (controller && IsMainThread() && mode < 4 && Core::CommandDispatcher::Get().IsAvailable() &&
                    IsInstanceOfProfileClass(controller, kShooterPlayerControllerClassGlobal))
                {
                    std::string copied;
                    void* connection = nullptr;
                    ReplyContext context{controller, nullptr};
                    if (ReadPointer(controller, kNetConnectionOffset, connection) && connection &&
                        (context.Connection = connection) && UE::NativeChatText::Decode(message, copied) &&
                        !copied.empty() && copied.front() == '/')
                    {
                        // A plugin may cause nested engine calls. Capture identity
                        // before its entry and use only these copies afterward.
                        const auto player = CapturePlayer(controller);
                        const Core::CommandPlayerSnapshot snapshot{
                            player.IdentityFlags, player.PlayerName, player.PlatformId};
                        if (Core::CommandDispatcher::Get().Dispatch(controller, copied, mode,
                                ReplyToOrigin, &context, &snapshot) > 0)
                        {
                            handled = true;
                            const auto sequence = state.CommandCount.fetch_add(1, std::memory_order_relaxed) + 1;
                            auto details = PlayerDetails(player);
                            details["sequence"] = sequence;
                            OBELISK_INFO("Native command player: {}", details.dump());
                            OBELISK_INFO("Native chat command handled. sequence={} mode={}", sequence, mode);
                            return; // Registered commands are consumed; ordinary chat stays native.
                        }
                    }
                }
            }
            catch (const std::exception& error)
            {
                OBELISK_ERROR("Native command dispatch failed: {}", error.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Native command dispatch failed with unknown exception.");
            }
            if (!handled && state.Original)
                state.Original(controller, message, mode);
        }
    }

    bool Install()
    {
        auto& state = GetState();
        if (state.Installed.load(std::memory_order_acquire))
            return true;
        if (!Runtime::CurrentExecutableMatches(kBinarySha))
        {
            OBELISK_ERROR("Native commands disabled: actual executable SHA256 does not match supported profile.");
            return false;
        }
        const auto module = Memory::GetMainModuleInfo();
        if (!module.found)
            return false;
        if (!ValidateMappedLifecycleProfile(module.imageBase))
        {
            OBELISK_ERROR("Native player backend disabled: mapped owner/layout proofs differ from the exact binary profile.");
            return false;
        }
        auto* receive = reinterpret_cast<void*>(module.imageBase + kReceiveAddress - kElfImageBase);
        auto* reply = reinterpret_cast<void*>(module.imageBase + kReplyAddress - kElfImageBase);
        // The signature was proved unique in this exact, SHA-pinned ELF. Verify
        // its complete bytes at the mapped entry instead of scanning only the
        // final /proc/maps segment: an earlier code patch splits executable VMAs.
        std::array<uint8_t, kReceiveSignature.size()> receiveBytes;
        if (!Memory::ReadExact(receiveBytes.data(), receive, receiveBytes.size()) ||
            receiveBytes != kReceiveSignature)
        {
            OBELISK_ERROR("Native commands disabled: mapped receive function signature differs from the exact binary profile.");
            return false;
        }
        std::array<uint8_t, kReplyPrologue.size()> replyBytes;
        std::array<uint8_t, kReplyFNameBinding.size()> nameBytes;
        if (!Memory::ReadExact(replyBytes.data(), reply, replyBytes.size()) ||
            replyBytes != kReplyPrologue ||
            !Memory::ReadExact(nameBytes.data(), reinterpret_cast<const uint8_t*>(reply) + 0x98,
                               nameBytes.size()) || nameBytes != kReplyFNameBinding)
        {
            OBELISK_ERROR("Native commands disabled: directed reply RPC profile mismatch.");
            return false;
        }
        state.Send = reinterpret_cast<Reply>(reply);
        state.ImageBase = module.imageBase;
        state.GetUniqueId = reinterpret_cast<UniqueId>(module.imageBase + kUniqueIdAddress - kElfImageBase);
        state.FreeString = reinterpret_cast<Free>(module.imageBase + kFreeAddress - kElfImageBase);
        if (!state.Hook.Install(receive, reinterpret_cast<void*>(ReceiveDetour), kReceivePrologue))
        {
            state.Send = nullptr;
            OBELISK_ERROR("Native command receive hook installation failed: {}", state.Hook.LastError());
            return false;
        }
        state.Original = reinterpret_cast<Receive>(state.Hook.Trampoline());
        const auto epoch = std::chrono::steady_clock::now().time_since_epoch().count();
        state.LifecycleProcessEpoch = epoch > 0 ? static_cast<uint64_t>(epoch) : 1;
        state.Installed.store(true, std::memory_order_release);
        Core::CommandDispatcher::Get().SetAvailable(true);
        Core::CommandDispatcher::Get().SetPlayerSnapshotsAvailable(true);
        Core::PlayerLifecycleDispatcher::Get().SetAvailable(true);
        OBELISK_INFO("Native commands installed for actual SHA256 {}. receive={} reply={} patch_bytes=20",
                     kBinarySha, receive, reply);
        return true;
    }

    bool IsInstalled() noexcept
    {
        return GetState().Installed.load(std::memory_order_acquire);
    }

    void CapturePlayerLifecycle(void* object, void* function, void* parameters,
                                PlayerLifecycleFrame& frame) noexcept
    {
        frame = {};
        try
        {
            auto& state = GetState();
            if (!state.Installed.load(std::memory_order_acquire) || !IsMainThread() ||
                !Core::PlayerLifecycleDispatcher::Get().IsAvailable() ||
                !object || !function || !parameters)
                return;
            struct FName { int32_t Index; int32_t Number; };
            FName name{};
            if (!ReadField(function, 0x18, name))
                return;
            struct EventProfile
            {
                uintptr_t FNameGlobal;
                PlayerLifecycleFrame::Event Selected;
                uint16_t ParameterBytes;
                uint8_t NumParms;
                uint16_t ReturnValueOffset;
                uintptr_t DeclarationGlobal;
            };
            constexpr std::array<EventProfile, 3> events{{
                {0x58ed3d0, PlayerLifecycleFrame::Event::HandleNewPlayer, 26, 5, 25, kShooterGameModeClassGlobal},
                {0x58ed3e0, PlayerLifecycleFrame::Event::Logout, 8, 1, 0xffff, kShooterGameModeClassGlobal},
                {0x59a7578, PlayerLifecycleFrame::Event::PostLogin, 8, 1, 0xffff, kGameModeClassGlobal}
            }};
            const EventProfile* selected = nullptr;
            for (const auto& event : events)
            {
                FName expected{};
                if (Memory::ReadExact(&expected, ProfileAddress(event.FNameGlobal), sizeof(expected)) &&
                    expected.Index > 0 && name.Index == expected.Index && name.Number == expected.Number)
                {
                    selected = &event;
                    break;
                }
            }
            if (!selected || !ValidateFunctionOwner(object, function, selected->DeclarationGlobal))
                return;
            uint16_t parameterBytes = 0;
            uint16_t returnOffset = 0xffff;
            uint8_t numParms = 0;
            if (!ReadField(function, 0x98, parameterBytes) || parameterBytes != selected->ParameterBytes ||
                !ReadField(function, 0x96, numParms) || numParms != selected->NumParms ||
                !ReadField(function, 0x9a, returnOffset) || returnOffset != selected->ReturnValueOffset)
                return;
            void* controller = nullptr;
            void* vtable = nullptr;
            void* receive = nullptr;
            const auto expectedReceive = const_cast<void*>(ProfileAddress(kReceiveAddress));
            if (!Memory::ReadExact(&controller, parameters, sizeof(controller)) ||
                !IsInstanceOfProfileClass(controller, kShooterPlayerControllerClassGlobal) ||
                !ReadPointer(controller, 0, vtable) || !ReadPointer(vtable, 0x1360, receive) ||
                receive != expectedReceive)
                return;
            uint8_t fromLogin = 0;
            if (selected->Selected == PlayerLifecycleFrame::Event::HandleNewPlayer &&
                !ReadField(parameters, 24, fromLogin))
                return;

            auto player = CapturePlayer(controller);
            if (!player.ControllerClassValidated || !player.MainThread)
                return;
            static_assert(OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE == OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE);
            static_assert(OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE == OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE);
            frame.PlayerName = std::move(player.PlayerName);
            frame.PlatformId = std::move(player.PlatformId);
            frame.ParameterBytes = parameterBytes;
            frame.NumParms = numParms;
            frame.ReturnValueOffset = returnOffset;
            frame.ProcessEpoch = state.LifecycleProcessEpoch;
            frame.PlayerStateAvailable = player.PlayerStateAvailable;
            frame.PlayerStateClassValidated = player.PlayerStateClassValidated;
            frame.FromLoginValue = fromLogin;
            frame.Flags = player.IdentityFlags | OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED |
                OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED | OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD;
            if (player.NetConnectionAvailable)
                frame.Flags |= OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE;
            frame.Selected = selected->Selected;

            // Logout identity must be copied and published before the engine
            // cleanup. Connection availability is informative, never required.
            if (frame.Selected == PlayerLifecycleFrame::Event::Logout)
                EmitLifecycle(frame, OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED);
            OBELISK_INFO("Native player lifecycle observation: {}", LifecycleDetails(frame, "entered").dump());
        }
        catch (...)
        {
            frame = {};
            // Capture and plugin failures cannot suppress or alter the UE call.
        }
    }

    void CompletePlayerLifecycle(PlayerLifecycleFrame& frame, const void* parameters,
                                 bool originalReturnedNormally) noexcept
    {
        if (frame.Selected == PlayerLifecycleFrame::Event::None)
            return;
        if (!originalReturnedNormally)
        {
            frame = {};
            return;
        }
        try
        {
            // Use only entry-owned identity/quality copies. The original may
            // have cleared its player state or destroyed the actor; do not
            // dereference any object or call UE identity functions here.
            if (frame.Selected == PlayerLifecycleFrame::Event::PostLogin)
            {
                frame.Flags |= OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED;
                EmitLifecycle(frame, OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED);
            }
            auto details = LifecycleDetails(frame, "returned");
            details["original_called"] = true;
            if (frame.Selected == PlayerLifecycleFrame::Event::HandleNewPlayer)
            {
                uint8_t returnedValue = 0;
                if (ReadField(parameters, frame.ReturnValueOffset, returnedValue))
                {
                    details["return_value"] = returnedValue;
                    details["return_value_canonical"] = returnedValue <= 1;
                    if (frame.FromLoginValue <= 1 && returnedValue <= 1)
                    {
                        details["handler_returned_true"] = returnedValue == 1;
                        details["login_handler_accepted"] = frame.FromLoginValue == 1 && returnedValue == 1;
                    }
                }
                // Handler acceptance is not authentication or session creation.
                details["authentication_proven"] = false;
            }
            OBELISK_INFO("Native player lifecycle observation: {}", details.dump());
        }
        catch (...)
        {
            // Diagnostic/publication failures never escape into the UE frame.
        }
        frame = {};
    }
}
