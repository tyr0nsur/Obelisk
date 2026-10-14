#pragma once

#include <cstdint>
#include <string>

namespace Obelisk::Hooks::NativeChatHook
{
    // Startup only, exact binary profile. Deliberately has no hot-uninstall API.
    bool Install();
    bool IsInstalled() noexcept;
    // Private, per-ProcessEvent owned copies. No UE object, function, controller
    // or player-state pointer survives capture in this frame. Nested invocations
    // each own a distinct frame; copied identities convey no session authority.
    struct PlayerLifecycleFrame
    {
        enum class Event : uint8_t { None, HandleNewPlayer, PostLogin, Logout };
        Event Selected = Event::None;
        uint16_t ParameterBytes = 0;
        uint16_t ReturnValueOffset = 0xffff;
        uint8_t NumParms = 0;
        uint64_t Flags = 0;
        uint64_t Sequence = 0;
        uint64_t ProcessEpoch = 0;
        uint64_t ChatSessionToken = 0; // private registry token; no UE pointer
        bool PlayerStateAvailable = false;
        bool PlayerStateClassValidated = false;
        uint8_t FromLoginValue = 0;
        std::string PlayerName;
        std::string PlatformId;
    };

    // Arguments are borrowed only during these calls. Capture emits logout
    // before original; completion emits post-login only after original returned.
    void CapturePlayerLifecycle(void* object, void* function, void* parameters,
                                PlayerLifecycleFrame& frame) noexcept;
    void CompletePlayerLifecycle(PlayerLifecycleFrame& frame, const void* parameters,
                                 bool originalReturnedNormally) noexcept;
}
