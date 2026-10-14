#include "hooks/NativeChatHook.h"
#include "core/PlayerLifecycleDispatcher.h"
#include "runtime/Logger.h"

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>

namespace
{
    using Obelisk::Hooks::NativeChatHook::PlayerLifecycleFrame;
    using Obelisk::Hooks::NativeChatHook::CompletePlayerLifecycle;
    struct CopiedEvent
    {
        uint32_t Kind;
        uint64_t Flags;
        uint64_t Sequence;
        uint64_t ProcessEpoch;
        std::string Name;
        std::string Id;
    };
    struct Context
    {
        std::vector<CopiedEvent> Events;
        PlayerLifecycleFrame* Nested = nullptr;
        const void* InaccessibleParameters = nullptr;
        bool OuterViewSurvivedNested = false;
    };
    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }
    PlayerLifecycleFrame EntryCopy(PlayerLifecycleFrame::Event selected,
                                   const std::string& name, const std::string& id)
    {
        PlayerLifecycleFrame frame;
        frame.Selected = selected;
        frame.ParameterBytes = 8;
        frame.NumParms = 1;
        frame.ProcessEpoch = 123;
        frame.PlayerName = name;
        frame.PlatformId = id;
        frame.Flags = OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED |
            OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED |
            OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD |
            OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE |
            OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE;
        return frame;
    }
    void Observe(const ObeliskPlayerLifecycleEvent* event, void* data)
    {
        auto& context = *static_cast<Context*>(data);
        const std::string entryName(event->player_name.data, event->player_name.size);
        context.Events.push_back({event->kind, event->flags, event->sequence, event->process_epoch,
                                  entryName, {event->platform_id.data, event->platform_id.size}});
        if (context.Nested)
        {
            auto* nested = context.Nested;
            context.Nested = nullptr;
            CompletePlayerLifecycle(*nested, context.InaccessibleParameters, true);
            context.OuterViewSurvivedNested =
                std::string(event->player_name.data, event->player_name.size) == entryName;
        }
    }
    void ThrowingPlugin(const ObeliskPlayerLifecycleEvent*, void*)
    {
        throw std::runtime_error("intentional plugin exception");
    }
    void RequireCleared(const PlayerLifecycleFrame& frame)
    {
        Require(frame.Selected == PlayerLifecycleFrame::Event::None && frame.Flags == 0 &&
                frame.Sequence == 0 && frame.PlayerName.empty() && frame.PlatformId.empty(),
                "completed/skipped frame retained its observation");
    }
}

int main()
{
    // This exercises completion's real adapter/dispatcher boundary with owned
    // entry fixtures. It does not exercise ELF-profile capture or prove gameplay.
    char rootTemplate[] = "/tmp/obelisk_native_lifecycle_frames.XXXXXX";
    char* root = mkdtemp(rootTemplate);
    Require(root != nullptr, "mkdtemp failed");
    setenv("OBELISK_ROOT", root, 1);
    Obelisk::Logger::Init();
    const long pageSize = sysconf(_SC_PAGESIZE);
    Require(pageSize > 0, "page size unavailable");
    void* inaccessible = mmap(nullptr, static_cast<size_t>(pageSize), PROT_NONE,
                              MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    Require(inaccessible != MAP_FAILED, "mmap failed");

    auto& dispatcher = Obelisk::Core::PlayerLifecycleDispatcher::Get();
    dispatcher.SetAvailable(true);
    Context context;
    context.InaccessibleParameters = inaccessible;
    int owner = 0;
    const auto registration = dispatcher.Register(&owner, Observe, &context);
    Require(registration != 0, "lifecycle registration failed");

    auto skipped = EntryCopy(PlayerLifecycleFrame::Event::PostLogin, "skipped", "opaque-skipped");
    CompletePlayerLifecycle(skipped, inaccessible, false);
    Require(context.Events.empty(), "skipped/missing original published login");
    RequireCleared(skipped);

    std::string sourceName = "outer-player";
    std::string sourceId = "opaque-outer";
    auto outer = EntryCopy(PlayerLifecycleFrame::Event::PostLogin, sourceName, sourceId);
    sourceName.assign("mutated-after-entry");
    sourceId.clear();
    auto nested = EntryCopy(PlayerLifecycleFrame::Event::PostLogin, "inner-player", "opaque-inner");
    context.Nested = &nested;
    CompletePlayerLifecycle(outer, inaccessible, true);
    Require(context.Events.size() == 2, "nested completion lost or repeated an event");
    Require(context.Events[0].Name == "outer-player" && context.Events[0].Id == "opaque-outer" &&
            context.Events[1].Name == "inner-player" && context.Events[1].Id == "opaque-inner",
            "nested frame or post-entry mutation replaced copied identity");
    Require(context.OuterViewSurvivedNested, "nested event invalidated outer callback views");
    Require(context.Events[0].Kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED &&
            (context.Events[0].Flags & OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED) &&
            context.Events[1].Sequence > context.Events[0].Sequence &&
            context.Events[0].Sequence != 0 && context.Events[0].ProcessEpoch == 123,
            "completion quality/order/context incorrect");
    RequireCleared(outer);
    RequireCleared(nested);

    auto logout = EntryCopy(PlayerLifecycleFrame::Event::Logout, "logout-player", "opaque-logout");
    CompletePlayerLifecycle(logout, inaccessible, true);
    Require(context.Events.size() == 2, "logout returned phase published a second entry observation");
    RequireCleared(logout);
    auto handler = EntryCopy(PlayerLifecycleFrame::Event::HandleNewPlayer, "handler-player", "opaque-handler");
    handler.ParameterBytes = 26;
    handler.NumParms = 5;
    handler.ReturnValueOffset = 25;
    handler.FromLoginValue = 1;
    CompletePlayerLifecycle(handler, inaccessible, true);
    Require(context.Events.size() == 2, "handler observation became an independent login");
    RequireCleared(handler);

    int throwingOwner = 0;
    const auto throwingRegistration = dispatcher.Register(&throwingOwner, ThrowingPlugin, nullptr);
    Require(throwingRegistration != 0, "throwing fixture registration failed");
    auto survivesFailure = EntryCopy(PlayerLifecycleFrame::Event::PostLogin, "after-failure", "opaque-after");
    CompletePlayerLifecycle(survivesFailure, inaccessible, true);
    Require(context.Events.size() == 3 && context.Events.back().Name == "after-failure",
            "plugin exception escaped completion or prevented observation");
    RequireCleared(survivesFailure);

    dispatcher.UnregisterCallbacksForOwner(&throwingOwner);
    dispatcher.UnregisterCallbacksForOwner(&owner);
    dispatcher.SetAvailable(false);
    Require(munmap(inaccessible, static_cast<size_t>(pageSize)) == 0, "munmap failed");
    Obelisk::Logger::Shutdown();
    std::filesystem::remove_all(root);
    std::cout << "NativePlayerLifecycleFrameTests passed\n";
}
