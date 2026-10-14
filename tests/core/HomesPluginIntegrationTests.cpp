#include "core/PluginManager.h"
#include "core/ChatSessionRegistry.h"

#include <dlfcn.h>
#include <link.h>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    using namespace Obelisk::Core;
    namespace fs = std::filesystem;
    void Require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
    auto Deadline() { return std::chrono::steady_clock::now() + std::chrono::seconds(2); }

    class NativeLoader final : public PluginManager::LibraryLoader
    {
    public:
        explicit NativeLoader(CommandDispatcher& commands) : Commands(commands) {}
        void* Open(const fs::path& path, std::string& error) override
        {
            auto* handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
            if (!handle) error = dlerror();
            return handle;
        }
        void* Resolve(void* handle, const char* name, std::string& error) override
        {
            auto* symbol = dlsym(handle, name); if (!symbol) error = "missing symbol"; return symbol;
        }
        void* GetSymbolOwner(void* handle, void* symbol) override
        {
            link_map* primary = nullptr; Dl_info info{};
            return dlinfo(handle, RTLD_DI_LINKMAP, &primary) == 0 && primary && dladdr(symbol, &info) &&
                info.dli_fbase == reinterpret_cast<void*>(primary->l_addr) ? info.dli_fbase : nullptr;
        }
        bool Close(void* handle, std::string& error) override
        {
            CleanBeforeClose = CleanBeforeClose && Commands.SubscriptionCount() == 0;
            if (!dlclose(handle)) { ++Closed; return true; }
            error = dlerror(); return false;
        }
        CommandDispatcher& Commands;
        bool CleanBeforeClose = true;
        size_t Closed = 0;
    };
    struct Environment
    {
        struct Value { const char* Name; bool Present; std::string Text; };
        std::vector<Value> Values;
        explicit Environment(const fs::path& root)
        {
            for (const auto* name : {"OBELISK_ROOT", "OBELISK_CONFIG_DIR", "OBELISK_INSTANCE_ID"})
            {
                const auto* value = getenv(name); Values.push_back({name, value != nullptr, value ? value : ""});
            }
            setenv("OBELISK_ROOT", root.c_str(), 1);
            setenv("OBELISK_CONFIG_DIR", (root / "config").c_str(), 1);
            setenv("OBELISK_INSTANCE_ID", "homes-test", 1);
        }
        ~Environment()
        {
            for (const auto& value : Values)
                if (value.Present) setenv(value.Name, value.Text.c_str(), 1); else unsetenv(value.Name);
        }
    };
    struct Reply { void* Controller; std::string Text; };
    bool CaptureReply(void* controller, std::string_view text, void* data) noexcept
    {
        try { static_cast<std::vector<Reply>*>(data)->push_back({controller, std::string(text)}); return true; }
        catch (...) { return false; }
    }
    struct EndpointState
    {
        ChatSessionRegistry::Endpoint Endpoint;
        ObeliskCommandWorldInfo Pose{};
        bool Connected = true;
    };
    struct NativeState
    {
        std::vector<EndpointState> Endpoints;
        bool PoseAvailable = true;
        bool AcceptTravel = false;
        size_t TravelCalls = 0;
        void* TravelOrigin = nullptr;
        ObeliskCommandWorldInfo TravelDestination{};
    };
    bool ValidateEndpoint(const ChatSessionRegistry::Endpoint& endpoint, void* data) noexcept
    {
        for (const auto& current : static_cast<NativeState*>(data)->Endpoints)
            if (current.Connected && current.Endpoint.Controller == endpoint.Controller &&
                current.Endpoint.Connection == endpoint.Connection && current.Endpoint.PlayerState == endpoint.PlayerState)
                return true;
        return false;
    }
    bool NoNetworkSend(const ChatSessionRegistry::Endpoint&, std::string_view, void*) noexcept { return true; }
    bool CopyWorldInfo(void* controller, ObeliskCommandWorldInfo* out, void* data) noexcept
    {
        auto& state = *static_cast<NativeState*>(data);
        if (!state.PoseAvailable) return false;
        for (const auto& current : state.Endpoints)
            if (current.Connected && current.Endpoint.Controller == controller) { *out = current.Pose; return true; }
        return false;
    }
    bool AcceptSelfTravel(void* controller, const ObeliskCommandWorldInfo* destination, void* data) noexcept
    {
        auto& state = *static_cast<NativeState*>(data);
        ++state.TravelCalls;
        state.TravelOrigin = controller; state.TravelDestination = *destination;
        if (!state.AcceptTravel) return false;
        for (auto& current : state.Endpoints)
            if (current.Connected && current.Endpoint.Controller == controller &&
                destination->process_epoch == current.Pose.process_epoch && destination->session_token == current.Pose.session_token)
            {
                current.Pose = *destination; return true;
            }
        return false;
    }
    void Config(const fs::path& root, std::string instance = "homes-test", unsigned quota = 3, unsigned cooldown = 30)
    {
        const nlohmann::json value{{"enabled", true}, {"allow_all_instances", false},
            {"instance_allowlist", {instance}}, {"max_homes", quota}, {"cooldown_seconds", cooldown}};
        std::ofstream(root / "config/oHomes/config.json") << value.dump();
    }
}

void TestNativeHomesPluginIntegration()
{
    const auto root = fs::temp_directory_path() /
        ("ObeliskHomes_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directories(root / "plugins"); fs::create_directories(root / "config/oHomes");
    Environment environment(root);
    ChatEventDispatcher chat; CommandDispatcher commands; PlayerLifecycleDispatcher lifecycle;
    ChatSessionRegistry sessions;
    constexpr uint64_t epoch = 991;
    int first, second, firstConnection, secondConnection, replacementConnection, firstState, secondState;
    NativeState native;
    native.Endpoints = {{{&first, &firstConnection, &firstState}}, {{&second, &secondConnection, &secondState}}};
    Require(sessions.Configure(epoch, ValidateEndpoint, NoNetworkSend, &native), "Homes fixture registry configuration failed");
    const auto firstToken = sessions.Observe(native.Endpoints[0].Endpoint, "First");
    const auto secondToken = sessions.Observe(native.Endpoints[1].Endpoint, "Second");
    Require(firstToken && secondToken && firstToken != secondToken, "Homes fixture did not create distinct live sessions");
    native.Endpoints[0].Pose = {OBELISK_COMMAND_WORLD_INFO_ABI_VERSION, sizeof(ObeliskCommandWorldInfo),
        OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE | OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE,
        100.0f, -20.0f, 50.0f, 0, 10.0f, 20.0f, 30.0f, 0, epoch, firstToken};
    native.Endpoints[1].Pose = {OBELISK_COMMAND_WORLD_INFO_ABI_VERSION, sizeof(ObeliskCommandWorldInfo),
        OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE | OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE,
        900.0f, 400.0f, 150.0f, 0, 1.0f, 2.0f, 3.0f, 0, epoch, secondToken};
    commands.SetAvailable(true); commands.SetChatSessionRegistry(&sessions);
    commands.SetWorldInfoAvailable(true); commands.SetSelfTeleportAvailable(true);
    NativeLoader loader(commands);
    {
        PluginManager manager(loader, chat, commands, lifecycle);
        manager.LoadPlugins((root / "plugins").string());
        fs::copy_file(OBELISK_HOMES_PLUGIN_PATH, root / "plugins/oHomes.so");
        Config(root, "other-instance");
        Require(!manager.ExecuteOperation("start", "oHomes", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "Homes escaped the explicit instance allowlist");
        Config(root);
        Require(manager.ExecuteOperation("start", "oHomes", Deadline())["ok"] && commands.SubscriptionCount() == 4,
            "Homes did not register its four scoped commands");
        std::vector<Reply> replies;
        CommandRuntimeContext firstContext, secondContext;
        firstContext.ChatSessionToken = firstToken; firstContext.WorldInfo = CopyWorldInfo;
        firstContext.Data = &native; firstContext.Teleport = AcceptSelfTravel;
        secondContext = firstContext; secondContext.ChatSessionToken = secondToken;
        auto invoke = [&](void* controller, std::string_view message, CommandRuntimeContext* context = nullptr) {
            if (!context) context = controller == &first ? &firstContext : &secondContext;
            return commands.Dispatch(controller, message, 0, CaptureReply, &replies, nullptr, context);
        };
        Require(invoke(&first, "/SETHOME base") == 1 && replies.back().Controller == &first &&
            replies.back().Text.find("guardado") != std::string::npos, "Homes failed to save the copied current pose");
        Require(invoke(&second, "/homes") == 1 && replies.back().Controller == &second &&
            replies.back().Text.find("Sin puntos") != std::string::npos && invoke(&second, "/home base") == 1 &&
            replies.back().Text.find("No existe") != std::string::npos && native.TravelCalls == 0,
            "Homes exposed or used another session's saved point");
        Require(invoke(&first, "/sethome two") == 1 && invoke(&first, "/sethome three") == 1 &&
            invoke(&first, "/sethome four") == 1 && replies.back().Text.find("límite") != std::string::npos,
            "Homes failed to apply the configured per-session quota");
        Require(invoke(&first, "/sethome base") == 1 && replies.back().Text.find("guardado") != std::string::npos,
            "Homes counted updating an existing point as an extra quota entry");
        native.Endpoints[0].Pose.x = 777.0f; native.Endpoints[0].Pose.yaw = -90.0f;
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == 1 &&
            native.TravelOrigin == &first && native.TravelDestination.x == 100.0f &&
            native.TravelDestination.y == -20.0f && native.TravelDestination.z == 50.0f &&
            native.TravelDestination.yaw == 20.0f && native.TravelDestination.session_token == firstToken &&
            native.TravelDestination.process_epoch == epoch && replies.back().Text.find("No se pudo") != std::string::npos,
            "Homes used a stale/current-other pose or misidentified native travel rejection");
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == 2,
            "Homes consumed a success cooldown after rejected travel");
        native.AcceptTravel = true;
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == 3 &&
            replies.back().Text.find("confirmada") != std::string::npos && native.Endpoints[0].Pose.x == 100.0f,
            "Homes did not accept the successful mock native receipt");
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == 3 &&
            replies.back().Text.find("Espera") != std::string::npos,
            "Homes did not start its cooldown after accepted travel");
        Require(invoke(&second, "/sethome own") == 1 && invoke(&second, "/home own") == 1 &&
            native.TravelCalls == 4 && native.TravelOrigin == &second &&
            native.TravelDestination.session_token == secondToken && native.TravelDestination.x == 900.0f,
            "Homes applied another session's cooldown or destination");
        Require(invoke(&first, "/homes") == 1 && replies.back().Text.find("base") != std::string::npos &&
            replies.back().Text.find("three") != std::string::npos && replies.back().Text.find("four") == std::string::npos,
            "Homes listed points outside the saved quota");
        Require(invoke(&first, "/delhome two") == 1 && replies.back().Text.find("eliminado") != std::string::npos &&
            invoke(&first, "/homes") == 1 && replies.back().Text.find(" two") == std::string::npos,
            "Homes failed to delete an existing session point");
        const auto travelCalls = native.TravelCalls;
        Require(invoke(&first, "/home base second-player") == 1 && native.TravelCalls == travelCalls &&
            replies.back().Text.find("nombre") != std::string::npos && invoke(&first, "/homebased") == 0,
            "Homes accepted a target-player argument or overlapping prefix command");
        native.PoseAvailable = false;
        Require(invoke(&second, "/sethome missing") == 1 && replies.back().Text.find("no está disponible") != std::string::npos,
            "Homes saved a point when the current native pose was unavailable");
        native.PoseAvailable = true;
        native.Endpoints[1].Pose.session_token = firstToken;
        Require(invoke(&second, "/sethome mismatch") == 1 && replies.back().Text.find("no está disponible") != std::string::npos,
            "Homes accepted a pose copied for a different current session");
        native.Endpoints[1].Pose.session_token = secondToken;

        Require(manager.ExecuteOperation("pause", "oHomes", Deadline())["ok"] && invoke(&first, "/homes") == 0 &&
            commands.SubscriptionCount() == 4, "Homes pause discarded registrations or admitted a command");
        Require(manager.ExecuteOperation("resume", "oHomes", Deadline())["ok"] && invoke(&first, "/homes") == 1 &&
            replies.back().Text.find("base") != std::string::npos, "Homes pause/resume discarded current session points");
        sessions.InvalidateController(&first);
        const auto beforeDisconnectReply = replies.size();
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == travelCalls &&
            replies.size() == beforeDisconnectReply, "Homes moved or replied through an invalidated disconnected session");
        native.Endpoints[0].Endpoint.Connection = &replacementConnection;
        const auto replacementToken = sessions.Observe(native.Endpoints[0].Endpoint, "First");
        Require(replacementToken && replacementToken != firstToken, "Homes fixture reconnect reused an old token");
        firstContext.ChatSessionToken = replacementToken; native.Endpoints[0].Pose.session_token = replacementToken;
        Require(invoke(&first, "/home base") == 1 && native.TravelCalls == travelCalls &&
            replies.back().Text.find("No existe") != std::string::npos && invoke(&first, "/homes") == 1 &&
            replies.back().Text.find("Sin puntos") != std::string::npos,
            "Homes inherited saved points after reconnecting the same controller/name");
        Require(invoke(&first, "/sethome fresh") == 1 && replies.back().Text.find("guardado") != std::string::npos,
            "Homes failed to save a point in the replacement session");
        Require(manager.ExecuteOperation("reload", "oHomes", Deadline())["ok"] && invoke(&first, "/homes") == 1 &&
            replies.back().Text.find("Sin puntos") != std::string::npos && invoke(&second, "/homes") == 1 &&
            replies.back().Text.find("Sin puntos") != std::string::npos,
            "Homes reload carried temporary points into a fresh library generation");
        Require(manager.ExecuteOperation("stop", "oHomes", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "Homes stop retained callbacks");
        Config(root, "homes-test", 0);
        Require(!manager.ExecuteOperation("start", "oHomes", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "Homes accepted zero quota or left partial callbacks");
        std::ofstream(root / "config/oHomes/config.json") <<
            R"({"enabled":true,"allow_all_instances":false,"instance_allowlist":["homes-test"],"max_homes":3,"cooldown_seconds":30,"unknown":1})";
        Require(!manager.ExecuteOperation("start", "oHomes", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "Homes accepted an unknown config option");
        Config(root);
        Require(manager.ExecuteOperation("start", "oHomes", Deadline())["ok"] && invoke(&first, "/homes") == 1 &&
            replies.back().Text.find("Sin puntos") != std::string::npos,
            "Homes restart after invalid config failed or reused earlier session points");
        for (const auto& reply : replies)
            Require(!reply.Text.empty() && reply.Text.size() <= 1024 && reply.Text.find('\0') == std::string::npos,
                "Homes emitted an oversized or NUL-containing response");
        manager.UnloadAll();
        Require(commands.SubscriptionCount() == 0 && loader.CleanBeforeClose && loader.Closed > 1,
            "Homes callback cleanup did not precede real library closure");
    }
    fs::remove_all(root);
}
