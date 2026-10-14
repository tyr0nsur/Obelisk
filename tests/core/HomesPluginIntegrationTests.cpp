#include "core/PluginManager.h"
#include "core/ChatSessionRegistry.h"

#include <dlfcn.h>
#include <link.h>
#include <algorithm>
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

    namespace CapacityFixture
    {
        struct Registration { uint64_t Handle; std::string Name; ObeliskCommandCallback Callback; void* Data; };
        struct Harness
        {
            std::vector<Registration> Registrations;
            std::vector<ObeliskChatSession> Roster;
            std::vector<std::string> Replies;
            uint64_t Current = 1, Owner = 7331, Invocation = 0, NextHandle = 0;
            size_t TravelCalls = 0, ListCalls = 0, TotalOverride = 0, WrittenOverride = 0;
            bool ListAvailable = true;
        };
        Harness* currentHarness = nullptr;
        ObeliskChatSession Session(uint64_t token)
        { return {OBELISK_CHAT_SESSION_ABI_VERSION, sizeof(ObeliskChatSession), token, 991}; }
        bool Scope(uint64_t owner, uint64_t invocation)
        { return currentHarness && owner == currentHarness->Owner && invocation && invocation == currentHarness->Invocation; }
        uint64_t Register(uint64_t owner, const char* name, uint64_t flags, ObeliskCommandCallback callback, void* data)
        {
            if (!currentHarness || owner != currentHarness->Owner || !name || !callback || flags !=
                (OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE)) return 0;
            const auto handle = ++currentHarness->NextHandle;
            currentHarness->Registrations.push_back({handle, name, callback, data}); return handle;
        }
        bool Unregister(uint64_t owner, uint64_t handle)
        {
            if (!currentHarness || owner != currentHarness->Owner) return false;
            const auto before = currentHarness->Registrations.size();
            std::erase_if(currentHarness->Registrations, [&](const auto& item) { return item.Handle == handle; });
            return before != currentHarness->Registrations.size();
        }
        bool Reply(uint64_t owner, uint64_t invocation, ObeliskCommandStringView value)
        {
            if (!Scope(owner, invocation) || !value.data) return false;
            currentHarness->Replies.emplace_back(value.data, value.size); return true;
        }
        bool Current(uint64_t owner, uint64_t invocation, ObeliskChatSession* out)
        { if (!Scope(owner, invocation) || !out) return false; *out = Session(currentHarness->Current); return true; }
        bool List(uint64_t owner, uint64_t invocation, ObeliskChatSession* out, size_t capacity, size_t* written, size_t* total)
        {
            if (!Scope(owner, invocation) || !out || !written || !total) return false;
            ++currentHarness->ListCalls;
            const auto copied = std::min(capacity, currentHarness->Roster.size());
            std::copy_n(currentHarness->Roster.begin(), copied, out);
            *written = currentHarness->WrittenOverride ? currentHarness->WrittenOverride : copied;
            *total = currentHarness->TotalOverride ? currentHarness->TotalOverride : currentHarness->Roster.size();
            return currentHarness->ListAvailable;
        }
        bool World(uint64_t owner, uint64_t invocation, ObeliskCommandWorldInfo* out)
        {
            if (!Scope(owner, invocation) || !out) return false;
            *out = {OBELISK_COMMAND_WORLD_INFO_ABI_VERSION, sizeof(*out), OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE,
                100, 200, 300, 0, 0, 0, 0, 0, 991, currentHarness->Current}; return true;
        }
        bool Travel(uint64_t owner, uint64_t invocation, const ObeliskCommandWorldInfo* pose)
        {
            if (!Scope(owner, invocation) || !pose || pose->session_token != currentHarness->Current || pose->process_epoch != 991) return false;
            ++currentHarness->TravelCalls; return true;
        }
        void Invoke(const char* verb, std::string message)
        {
            const auto found = std::find_if(currentHarness->Registrations.begin(), currentHarness->Registrations.end(),
                [&](const auto& registration) { return registration.Name == verb; });
            Require(found != currentHarness->Registrations.end(), "Capacity fixture command missing");
            ObeliskCommandInvocation invocation{OBELISK_COMMAND_INVOCATION_ABI_VERSION, sizeof(invocation), 0, 0, 41,
                {message.data(), message.size()}};
            currentHarness->Invocation = invocation.invocation_token; found->Callback(&invocation, found->Data); currentHarness->Invocation = 0;
        }
        void Run(const fs::path& root)
        {
            Harness harness; currentHarness = &harness;
            void* library = dlopen(OBELISK_HOMES_PLUGIN_PATH, RTLD_NOW | RTLD_LOCAL);
            Require(library, "Homes capacity regression real DSO load failed");
            const auto init = reinterpret_cast<bool(*)(ObeliskApi*, const ObeliskPluginInitContext*)>(dlsym(library, "ObeliskPlugin_Init"));
            const auto shutdown = reinterpret_cast<void(*)()>(dlsym(library, "ObeliskPlugin_Shutdown"));
            Require(init && shutdown, "Homes capacity regression lifecycle exports missing");
            ObeliskApi api{}; api.abi_version = OBELISK_API_ABI_VERSION; api.struct_size = sizeof(api);
            api.capabilities = OBELISK_API_CAPABILITY_CHAT_SESSIONS | OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE |
                OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS | OBELISK_API_CAPABILITY_COMMAND_REPLIES | OBELISK_API_CAPABILITY_COMMAND_SELF_TELEPORT;
            api.RegisterCommandWithOptionsWithOwnerTokenHandle = Register; api.UnregisterCommandWithOwnerToken = Unregister;
            api.ReplyToCommandWithOwnerToken = Reply; api.GetCommandChatSessionWithOwnerToken = Current;
            api.ListChatSessionsWithOwnerToken = List; api.GetCommandWorldInfoWithOwnerToken = World; api.TeleportCommandOriginWithOwnerToken = Travel;
            Config(root, "homes-test", 3, 3600);
            const auto directory = (root / "config/oHomes").string(), path = (root / "config/oHomes/config.json").string();
            const ObeliskPluginInitContext context{OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION, sizeof(context), directory.c_str(),
                path.c_str(), "homes-test", harness.Owner};
            Require(init(&api, &context), "Homes capacity regression plugin init failed");
            Invoke("/sethome", "/sethome keeper"); Invoke("/home", "/home keeper");
            Require(harness.TravelCalls == 1, "Homes capacity fixture could not establish a live cooldown");
            for (uint64_t token = 2; token <= 1024; ++token)
            {
                harness.Current = token; Invoke("/sethome", "/sethome retired");
                Require(harness.Replies.back().find("guardado") != std::string::npos, "Homes capacity fixture failed to fill historical sessions");
            }
            Require(harness.ListCalls == 0, "Homes needlessly scanned peers before capacity pressure");
            harness.Current = 1025;
            const std::vector<ObeliskChatSession> valid{Session(1), Session(1025)};
            harness.Roster = valid;
            auto rejected = [&] {
                harness.Current = 1025; Invoke("/sethome", "/sethome fresh");
                Require(harness.Replies.back().find("No se pueden guardar") != std::string::npos,
                    "Homes reclaimed history using an incomplete or invalid roster");
                harness.Current = 1; Invoke("/homes", "/homes");
                Require(harness.Replies.back().find("keeper") != std::string::npos,
                    "Homes discarded a live saved point after invalid roster output");
                Invoke("/home", "/home keeper");
                Require(harness.TravelCalls == 1 && harness.Replies.back().find("Espera") != std::string::npos,
                    "Homes reset a live cooldown while reclaiming disconnected sessions");
            };
            harness.ListAvailable = false; rejected(); harness.ListAvailable = true;
            harness.TotalOverride = 65; rejected(); harness.TotalOverride = 0;
            harness.WrittenOverride = OBELISK_CHAT_SESSION_LIST_MAX + 1; rejected(); harness.WrittenOverride = 0;
            harness.Roster.push_back(Session(1025)); rejected(); harness.Roster = valid;
            harness.Roster[0].process_epoch = 992; rejected(); harness.Roster = valid;
            harness.Roster[0].abi_version = 99; rejected(); harness.Roster = valid;
            harness.Roster[0].struct_size = sizeof(ObeliskChatSession) - 1; rejected(); harness.Roster = valid;
            harness.Roster[0].session_token = 0; rejected(); harness.Roster = {Session(1)};
            rejected(); harness.Roster = valid;
            harness.Current = 1025; Invoke("/sethome", "/sethome fresh");
            Require(harness.Replies.back().find("guardado") != std::string::npos,
                "Homes remained permanently full after the complete roster proved old sessions disconnected");
            Invoke("/home", "/home fresh");
            Require(harness.TravelCalls == 2 && harness.Replies.back().find("confirmada") != std::string::npos,
                "Homes reclaimed capacity but failed to keep the new session's point");
            harness.Current = 1; Invoke("/homes", "/homes");
            Require(harness.Replies.back().find("keeper") != std::string::npos, "Homes complete cleanup discarded another live session's point");
            Invoke("/home", "/home keeper");
            Require(harness.TravelCalls == 2 && harness.Replies.back().find("Espera") != std::string::npos,
                "Homes complete cleanup reset another live session's cooldown");
            harness.Current = 2; Invoke("/homes", "/homes");
            Require(harness.Replies.back().find("Sin puntos") != std::string::npos,
                "Homes complete cleanup retained the disconnected session history");
            shutdown();
            Require(harness.Registrations.empty() && dlclose(library) == 0, "Homes capacity fixture leaked callbacks or DSO mapping");
            currentHarness = nullptr;
        }
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
    CapacityFixture::Run(root);
    fs::remove_all(root);
}
