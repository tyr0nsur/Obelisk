#define OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
#include "core/PluginManager.h"
#include "core/EventManager.h"
#include "core/GameplayCallbackScope.h"
#include "extern/nlohmann/json.hpp"

#include <dlfcn.h>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace
{
    void Require(bool value, const char* message)
    {
        if (!value)
            throw std::runtime_error(message);
    }

    using NativeInit = bool (*)(ObeliskApi*, const ObeliskPluginInitContext*);
    NativeInit g_LegacyInit = nullptr;
    bool g_UseLegacyApi = false;
    std::vector<std::string>* g_PluginLogs = nullptr;
    void CapturePluginLog(const char* message)
    {
        if (g_PluginLogs && message)
            g_PluginLogs->emplace_back(message);
    }

    bool InitWithApiView(ObeliskApi* api, const ObeliskPluginInitContext* context)
    {
        ObeliskApi legacy{};
        constexpr auto oldPrefixSize = offsetof(ObeliskApi, GetCommandPlayerWithOwnerToken);
        std::memcpy(&legacy, api, g_UseLegacyApi ? oldPrefixSize : sizeof(legacy));
        if (g_UseLegacyApi)
        {
            legacy.struct_size = oldPrefixSize;
            legacy.capabilities &= (uint64_t{1} << 13) - 1;
        }
        if (g_PluginLogs)
            legacy.LogInfo = CapturePluginLog;
        return g_LegacyInit(&legacy, context);
    }

    class NativeLoader : public Obelisk::Core::PluginManager::LibraryLoader
    {
    public:
        NativeLoader(Obelisk::Core::CommandDispatcher& dispatcher, Obelisk::Core::PlayerLifecycleDispatcher& lifecycle)
            : Commands(dispatcher), Lifecycle(lifecycle) {}
        void* Open(const std::filesystem::path& path, std::string& error) override
        {
            void* handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
            if (!handle)
                error = dlerror();
            return handle;
        }
        void* Resolve(void* handle, const char* symbol, std::string& error) override
        {
            void* result = dlsym(handle, symbol);
            if (!result)
                error = "missing native plugin symbol";
            if (result && (LegacyCommandApi || PluginLogs) && std::strcmp(symbol, "ObeliskPlugin_Init") == 0)
            {
                g_LegacyInit = reinterpret_cast<NativeInit>(result);
                g_UseLegacyApi = LegacyCommandApi;
                g_PluginLogs = PluginLogs;
                return reinterpret_cast<void*>(InitWithApiView);
            }
            return result;
        }
        void* GetSymbolOwner(void*, void* symbol) override
        {
            if (symbol == reinterpret_cast<void*>(InitWithApiView))
                symbol = reinterpret_cast<void*>(g_LegacyInit);
            Dl_info info{};
            return dladdr(symbol, &info) ? info.dli_fbase : nullptr;
        }
        bool Close(void* handle, std::string& error) override
        {
            CleanBeforeClose = Commands.SubscriptionCount() == 0 && Lifecycle.SubscriptionCount() == 0;
            ++CloseCount;
            if (dlclose(handle) == 0)
                return true;
            error = dlerror();
            return false;
        }
        Obelisk::Core::CommandDispatcher& Commands;
        Obelisk::Core::PlayerLifecycleDispatcher& Lifecycle;
        bool CleanBeforeClose = false;
        int CloseCount = 0;
        bool LegacyCommandApi = false;
        std::vector<std::string>* PluginLogs = nullptr;
    };

    struct Reply { void* Controller; std::string Text; };
    bool Capture(void* controller, std::string_view text, void* data) noexcept
    {
        try
        {
            static_cast<std::vector<Reply>*>(data)->push_back({controller, std::string(text)});
            return true;
        }
        catch (...) { return false; }
    }

    struct LegacyCallbackState
    {
        Obelisk::Core::CommandDispatcher* Commands;
        Obelisk::Core::EventManager* Events;
        void* Owner;
        uint64_t Token = 0;
        const Obelisk::Core::GameplayCallbackScope* OuterScope = nullptr;
        size_t Calls = 0;
        bool Rejected = true;
        bool DepthPolicyPreserved = true;
        bool Restored = false;
    };

    bool InspectLegacyScope(void* caller, void*, void*)
    {
        using Obelisk::Core::GameplayCallbackFamily;
        using Obelisk::Core::GameplayCallbackScope;
        auto& state = *static_cast<LegacyCallbackState*>(caller);
        ++state.Calls;
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.Rejected = state.Rejected && !state.Commands->GetPlayer(state.Owner, state.Token, &player) &&
                         !state.Commands->Reply(state.Owner, state.Token, "legacy-misroute");
        state.DepthPolicyPreserved = state.DepthPolicyPreserved && GameplayCallbackScope::Current() &&
            GameplayCallbackScope::Current() != state.OuterScope &&
            !GameplayCallbackScope::IsInsideCallback(GameplayCallbackFamily::ProcessEvent) &&
            (state.OuterScope ? GameplayCallbackScope::IsInsideCallback(GameplayCallbackFamily::Command) :
                                !GameplayCallbackScope::IsInsideAnyCallback());
        return true;
    }

    bool ThrowLegacyCallback(void*, void*, void*) { throw std::runtime_error("legacy callback failure"); }

    void InvokeLegacyCallbacks(const ObeliskCommandInvocation* event, void* data)
    {
        auto& state = *static_cast<LegacyCallbackState*>(data);
        state.Token = event->invocation_token;
        state.OuterScope = Obelisk::Core::GameplayCallbackScope::Current();
        state.Events->TriggerPreProcessEvent(&state, nullptr, nullptr);
        state.Events->TriggerPostProcessEvent(&state, nullptr, nullptr);
        state.Events->TriggerPreProcessEvent(42, &state, nullptr, nullptr);
        state.Events->TriggerPostProcessEvent(42, &state, nullptr, nullptr);
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        state.Restored = Obelisk::Core::GameplayCallbackScope::Current() == state.OuterScope &&
            state.Commands->GetPlayer(state.Owner, state.Token, &player) &&
            state.Commands->Reply(state.Owner, state.Token, "legacy-restored");
        state.OuterScope = nullptr;
    }

    void TestCommandScopeAcrossProcessEventCallbacks()
    {
        Obelisk::Core::CommandDispatcher commands;
        commands.SetAvailable(true);
        commands.SetPlayerSnapshotsAvailable(true);
        Obelisk::Core::EventManager events;
        int owner, controller;
        LegacyCallbackState state{&commands, &events, &owner};
        Require(events.RegisterPreProcessEventOwned(&owner, InspectLegacyScope), "legacy pre registration failed");
        Require(events.RegisterPostProcessEventOwned(&owner, InspectLegacyScope), "legacy post registration failed");
        Require(events.RegisterPreProcessEventForNameIndexOwned(&owner, 42, InspectLegacyScope), "filtered pre registration failed");
        Require(events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, InspectLegacyScope), "filtered post registration failed");
        Require(events.RegisterPostProcessEventForNameIndexOwned(&owner, 42, ThrowLegacyCallback), "throw registration failed");
        Require(commands.Register(&owner, "/legacy-scope", InvokeLegacyCallbacks, &state), "legacy command registration failed");
        const Obelisk::Core::CommandPlayerSnapshot player{OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE, "Origin", {}};
        std::vector<Reply> replies;
        Require(commands.Dispatch(&controller, "/legacy-scope", 0, Capture, &replies, &player) == 1 &&
                state.Calls == 6 && state.Rejected && state.DepthPolicyPreserved && state.Restored &&
                replies.size() == 1 && replies.front().Text == "legacy-restored",
                "real nested ProcessEvent callback inherited command scope or failed to restore it");
        events.TriggerPreProcessEvent(&state, nullptr, nullptr);
        Require(state.Calls == 7 && state.DepthPolicyPreserved && state.Rejected &&
                !Obelisk::Core::GameplayCallbackScope::Current() &&
                !Obelisk::Core::GameplayCallbackScope::IsInsideAnyCallback(),
                "tracking-only ProcessEvent scope changed legacy depth policy or leaked after delivery");
        Require(events.UnregisterCallbacksForOwner(&owner) == 5, "legacy scope registrations not removed");
        commands.UnregisterCallbacksForOwner(&owner);
    }
}

void TestNativePingPluginIntegration()
{
    namespace fs = std::filesystem;
    const auto unique = std::chrono::steady_clock::now().time_since_epoch().count();
    const auto root = fs::temp_directory_path() / ("ObeliskNativePing_" + std::to_string(unique));
    fs::create_directories(root / "plugins");
    fs::create_directories(root / "config" / "oPing");
    fs::copy_file(OBELISK_PING_PLUGIN_PATH, root / "plugins" / "oPing.so");
    std::ofstream(root / "config" / "oPing" / "config.json") <<
        R"({"enabled":true,"allow_all_instances":false,"instance_allowlist":["arkserver"]})";
    setenv("OBELISK_CONFIG_DIR", (root / "config").c_str(), 1);
    setenv("OBELISK_ROOT", root.c_str(), 1);
    setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
    Obelisk::Core::ChatEventDispatcher chat;
    Obelisk::Core::CommandDispatcher commands;
    Obelisk::Core::PlayerLifecycleDispatcher lifecycle;
    NativeLoader loader(commands, lifecycle);
    {
        Obelisk::Core::PluginManager unverified(loader, chat, commands, lifecycle);
        Require(!(unverified.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_COMMAND_REPLIES),
                "unverified backend advertised reply capability");
        unverified.LoadPlugins((root / "plugins").string());
        Require(commands.SubscriptionCount() == 0 && loader.CloseCount == 1,
                "enabled oPing should fail init without verified backend");
    }
    commands.SetAvailable(true);
    loader.LegacyCommandApi = true;
    {
        Obelisk::Core::PluginManager manager(loader, chat, commands, lifecycle);
        Require(manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_COMMAND_REPLIES,
                "verified backend omitted command capability");
        Require(!(manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT),
                "command backend alone must not advertise player snapshots");
        manager.LoadPlugins((root / "plugins").string());
        Require(commands.SubscriptionCount() == 1, "real oPing .so did not register command");
        int playerA = 0, playerB = 0;
        std::vector<Reply> replies;
        Require(commands.Dispatch(&playerA, "/pingx", 0, Capture, &replies) == 0,
                "real plugin accepted unsafe prefix match");
        Require(commands.Dispatch(&playerA, "/ping", 0, Capture, &replies) == 1 &&
                commands.Dispatch(&playerB, "/ping", 0, Capture, &replies) == 1,
                "real native ping callbacks did not execute");
        Require(replies.size() == 2 && replies[0].Controller == &playerA && replies[1].Controller == &playerB &&
                replies[0].Text == "pong" && replies[1].Text == "pong", "oPing targeted reply mismatch");
        Require(commands.Dispatch(&playerA, "/whoami", 0, Capture, &replies) == 0,
                "whoami must be absent without player snapshot capability");
        manager.UnloadAll();
        Require(commands.SubscriptionCount() == 0 && loader.CloseCount == 2 && loader.CleanBeforeClose,
                "oPing callbacks were not removed before dlclose");
        Require(commands.Dispatch(&playerA, "/ping", 0, Capture, &replies) == 0,
                "unloaded plugin callback remained callable");
    }
    commands.SetPlayerSnapshotsAvailable(true);
    lifecycle.SetAvailable(true);
    loader.LegacyCommandApi = false;
    std::vector<std::string> pluginLogs;
    loader.PluginLogs = &pluginLogs;
    {
        Obelisk::Core::PluginManager manager(loader, chat, commands, lifecycle);
        Require(manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT,
                "verified player backend omitted snapshot capability");
        manager.LoadPlugins((root / "plugins").string());
        Require(commands.SubscriptionCount() == 2, "real plugin did not register ping and whoami");
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS) &&
                lifecycle.SubscriptionCount() == 1, "real native callback did not register for typed lifecycle");
        int playerA, playerB;
        constexpr auto flags = OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE |
                               OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE;
        const Obelisk::Core::CommandPlayerSnapshot first{flags, "\xc3\x81gata", "opaque-identity-A"};
        const Obelisk::Core::CommandPlayerSnapshot second{flags, "Bruno", "opaque-identity-B"};
        std::vector<Reply> replies;
        Require(commands.Dispatch(&playerA, "/whoamix", 0, Capture, &replies, &first) == 0,
                "whoami accepted prefix collision");
        Require(commands.Dispatch(&playerA, "/whoami", 0, Capture, &replies, &first) == 1 &&
                commands.Dispatch(&playerB, "/whoami", 0, Capture, &replies, &second) == 1,
                "real whoami callbacks missing");
        Require(replies.size() == 2 && replies[0].Controller == &playerA && replies[1].Controller == &playerB &&
                replies[0].Text == "Nombre: \xc3\x81gata | ID nativo: opaque-identity-A" &&
                replies[1].Text == "Nombre: Bruno | ID nativo: opaque-identity-B",
                "real whoami response used incorrect snapshot/controller");
        Require(commands.Dispatch(&playerA, "/ping", 0, Capture, &replies) == 1 && replies.back().Text == "pong",
                "missing identity snapshot broke ping");
        Require(commands.Dispatch(&playerA, "/whoami", 0, Capture, &replies) == 1 &&
                replies.back().Text == "Identidad no disponible para este comando.",
                "missing identity did not produce whoami fallback");
        constexpr auto quality = OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED |
                                 OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED |
                                 OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD;
        constexpr auto identity = OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE |
                                  OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE;
        Obelisk::Core::PlayerLifecycleSnapshot login{
            OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED,
            quality | identity | OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED,
            1, 42, "\xc3\x81gata\n\"quoted\"", "opaque-identity-A"};
        Require(lifecycle.Dispatch(login) == 1, "real lifecycle plugin callback did not receive login observation");
        auto logout = login;
        logout.Kind = OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED;
        logout.Flags &= ~OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED;
        logout.Sequence = 2;
        Require(lifecycle.Dispatch(logout) == 1, "real lifecycle plugin callback did not receive logout observation");
        size_t lifecycleLogs = 0;
        constexpr std::string_view prefix = "[oPing] Player lifecycle observation: ";
        for (const auto& log : pluginLogs)
        {
            if (!log.starts_with(prefix))
                continue;
            ++lifecycleLogs;
            Require(log.find('\n') == std::string::npos, "player name injected a log line");
            const auto document = nlohmann::json::parse(log.substr(prefix.size()));
            Require(document["observation_only"] == true && document["process_epoch"] == 42 &&
                    document["platform_id"] == "opaque-identity-A" &&
                    document["player_name"] == "\xc3\x81gata\n\"quoted\"" &&
                    document["kind"] == (lifecycleLogs == 1 ? "login_observed" : "logout_observed"),
                    "typed plugin changed copied observation or misrepresented its phase");
        }
        Require(lifecycleLogs == 2, "native plugin did not log both typed observations");
        manager.UnloadAll();
        Require(commands.SubscriptionCount() == 0 && lifecycle.SubscriptionCount() == 0 &&
                loader.CloseCount == 3 && loader.CleanBeforeClose,
                "both commands and lifecycle handle must be removed before real plugin dlclose");
        Require(commands.Dispatch(&playerA, "/whoami", 0, Capture, &replies, &first) == 0,
                "unloaded whoami callback remained callable");
        Require(lifecycle.Dispatch(login) == 0, "unloaded lifecycle plugin callback remained callable");
    }
    g_PluginLogs = nullptr;
    TestCommandScopeAcrossProcessEventCallbacks();
    fs::remove_all(root);
}
