#include "core/PluginManager.h"
#include "core/ChatSessionRegistry.h"

#include <dlfcn.h>
#include <link.h>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <limits>
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
            setenv("OBELISK_INSTANCE_ID", "world-test", 1);
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

    struct Observations
    {
        void* First = nullptr;
        void* Second = nullptr;
        std::vector<ChatSessionRegistry::Endpoint> Endpoints;
        ObeliskCommandWorldInfo FirstInfo{};
        ObeliskCommandWorldInfo SecondInfo{};
        bool Available = true;
        size_t Copies = 0;
        bool UnknownOrigin = false;
    };
    bool ValidateEndpoint(const ChatSessionRegistry::Endpoint& endpoint, void* data) noexcept
    {
        for (const auto& current : static_cast<Observations*>(data)->Endpoints)
            if (current.Controller == endpoint.Controller && current.Connection == endpoint.Connection &&
                current.PlayerState == endpoint.PlayerState) return true;
        return false;
    }
    bool NoNetworkSend(const ChatSessionRegistry::Endpoint&, std::string_view, void*) noexcept { return true; }
    bool CopyWorldInfo(void* controller, ObeliskCommandWorldInfo* out, void* data) noexcept
    {
        auto& value = *static_cast<Observations*>(data);
        ++value.Copies;
        if (!value.Available) return false;
        if (controller == value.First) *out = value.FirstInfo;
        else if (controller == value.Second) *out = value.SecondInfo;
        else { value.UnknownOrigin = true; return false; }
        return true;
    }

    void Config(const fs::path& root, std::string prefix = "ObeliskNative", std::string instance = "world-test")
    {
        const nlohmann::json value{{"enabled", true}, {"allow_all_instances", false},
            {"instance_allowlist", {instance}}, {"prefix", std::move(prefix)}};
        std::ofstream(root / "config/oWorldTools/config.json") << value.dump();
    }
}

void TestNativeWorldToolsPluginIntegration()
{
    const auto root = fs::temp_directory_path() /
        ("ObeliskWorldTools_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directories(root / "plugins"); fs::create_directories(root / "config/oWorldTools");
    Environment environment(root);
    ChatEventDispatcher chat; CommandDispatcher commands; PlayerLifecycleDispatcher lifecycle;
    ChatSessionRegistry sessions;
    int first, second, firstConnection, secondConnection, firstState, secondState;
    Observations observations;
    observations.First = &first; observations.Second = &second;
    observations.Endpoints = {{&first, &firstConnection, &firstState}, {&second, &secondConnection, &secondState}};
    Require(sessions.Configure(7, ValidateEndpoint, NoNetworkSend, &observations), "WorldTools fixture registry configuration failed");
    const auto firstToken = sessions.Observe(observations.Endpoints[0], "First");
    const auto secondToken = sessions.Observe(observations.Endpoints[1], "Second");
    Require(firstToken && secondToken && firstToken != secondToken, "WorldTools fixture did not create distinct sessions");
    commands.SetAvailable(true); commands.SetWorldInfoAvailable(true); commands.SetChatSessionRegistry(&sessions);
    NativeLoader loader(commands);
    {
        PluginManager manager(loader, chat, commands, lifecycle);
        manager.LoadPlugins((root / "plugins").string());
        fs::copy_file(OBELISK_WORLD_TOOLS_PLUGIN_PATH, root / "plugins/oWorldTools.so");
        Config(root, "ObeliskNative", "other-instance");
        Require(!manager.ExecuteOperation("start", "oWorldTools", Deadline())["ok"] &&
            commands.SubscriptionCount() == 0, "WorldTools escaped the instance allowlist");
        Config(root);
        Require(manager.ExecuteOperation("start", "oWorldTools", Deadline())["ok"] &&
            commands.SubscriptionCount() == 4, "WorldTools did not register its four scoped queries");

        observations.FirstInfo = {OBELISK_COMMAND_WORLD_INFO_ABI_VERSION, sizeof(ObeliskCommandWorldInfo),
            OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE | OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE |
                OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE | OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE |
                OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE,
            123.25f, -50.5f, 200.0f, 42, 1.0f, 2.0f, 3.0f, 0, 7, firstToken, 17, 29, 701, 0};
        observations.SecondInfo = {OBELISK_COMMAND_WORLD_INFO_ABI_VERSION, sizeof(ObeliskCommandWorldInfo),
            OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0.0f, 0.0f, 0, 7, secondToken};
        CommandRuntimeContext context, secondContext;
        context.ChatSessionToken = firstToken; context.WorldInfo = CopyWorldInfo; context.Data = &observations;
        secondContext = context; secondContext.ChatSessionToken = secondToken;
        std::vector<Reply> replies;
        auto invoke = [&](void* controller, std::string_view message, bool withContext = true) {
            return commands.Dispatch(controller, message, 0, CaptureReply, &replies, nullptr,
                withContext ? (controller == &first ? &context : &secondContext) : nullptr);
        };
        Require(invoke(&first, "/WHEREAMI") == 1 && replies.back().Controller == &first &&
            replies.back().Text.find("X=123.25 Y=-50.50 Z=200.00") != std::string::npos,
            "WorldTools did not copy or format the current command position");
        Require(invoke(&first, "/tribe") == 1 && replies.back().Text == "ObeliskNative: ID de tu tribu: 42" &&
            invoke(&second, "/tribe") == 1 && replies.back().Controller == &second &&
            replies.back().Text == "ObeliskNative: No perteneces a una tribu.",
            "WorldTools reused another player's tribe observation or treated zero as unavailable");
        Require(invoke(&first, "/dino") == 1 && replies.back().Text.find("17/29") != std::string::npos &&
            invoke(&first, "/structure") == 1 && replies.back().Text.find("701") != std::string::npos,
            "WorldTools failed to copy mounted dino or targeted structure IDs");
        Require(invoke(&second, "/whereami") == 1 && replies.back().Text.find("no esta disponible") != std::string::npos &&
            invoke(&second, "/dino") == 1 && replies.back().Text.find("Monta un dino") != std::string::npos &&
            invoke(&second, "/structure") == 1 && replies.back().Text.find("Apunta a una estructura") != std::string::npos,
            "WorldTools interpreted unavailable fields as zero-valued native observations");
        const auto copies = observations.Copies;
        Require(invoke(&first, "/whereami other-player") == 1 && observations.Copies == copies &&
            replies.back().Text.find("sin argumentos") != std::string::npos,
            "WorldTools accepted another player as a query argument");
        Require(invoke(&first, "/dinosaurs") == 0 && invoke(&first, "ordinary chat") == 0,
            "WorldTools consumed unrelated chat or prefix commands");
        observations.Available = false;
        Require(invoke(&first, "/whereami") == 1 && replies.back().Text.find("No se puede consultar") != std::string::npos,
            "WorldTools retained a previous world value after the backend became unavailable");
        observations.Available = true;
        Require(invoke(&first, "/whereami", false) == 1 && replies.back().Text.find("No se puede consultar") != std::string::npos,
            "WorldTools queried native data without a current private runtime context");
        observations.FirstInfo.x = std::numeric_limits<float>::quiet_NaN();
        Require(invoke(&first, "/whereami") == 1 && replies.back().Text.find("No se puede consultar") != std::string::npos,
            "WorldTools formatted a nonfinite native position");
        observations.FirstInfo.x = 123.25f;
        observations.FirstInfo.abi_version = 99;
        Require(invoke(&first, "/tribe") == 1 && replies.back().Text.find("No se puede consultar") != std::string::npos,
            "WorldTools interpreted an unsupported copied native ABI");
        observations.FirstInfo.abi_version = OBELISK_COMMAND_WORLD_INFO_ABI_VERSION;
        Require(!observations.UnknownOrigin, "WorldTools queried an unexpected origin");

        const auto repliesBeforePause = replies.size();
        Require(manager.ExecuteOperation("pause", "oWorldTools", Deadline())["ok"] &&
            invoke(&first, "/whereami") == 0 && replies.size() == repliesBeforePause && commands.SubscriptionCount() == 4,
            "WorldTools pause delivered a query or discarded registrations");
        Require(manager.ExecuteOperation("resume", "oWorldTools", Deadline())["ok"], "WorldTools resume failed");
        Config(root, "Informaci\xc3\xb3n");
        Require(manager.ExecuteOperation("reload", "oWorldTools", Deadline())["ok"] &&
            invoke(&first, "/TRIBE\t") == 1 && replies.back().Text == "Informaci\xc3\xb3n: ID de tu tribu: 42",
            "WorldTools fresh generation did not read the UTF-8 prefix config");
        Require(manager.ExecuteOperation("stop", "oWorldTools", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "WorldTools stop retained command registrations");
        Config(root, "bad\nprefix");
        Require(!manager.ExecuteOperation("start", "oWorldTools", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "WorldTools accepted a multiline prefix or left partial registrations");
        Config(root, std::string(65, 'x'));
        Require(!manager.ExecuteOperation("start", "oWorldTools", Deadline())["ok"] && commands.SubscriptionCount() == 0,
            "WorldTools accepted an oversized prefix");
        Config(root);
        Require(manager.ExecuteOperation("start", "oWorldTools", Deadline())["ok"], "WorldTools restart after invalid config failed");
        manager.UnloadAll();
        Require(commands.SubscriptionCount() == 0 && loader.CleanBeforeClose && loader.Closed > 1,
            "WorldTools command cleanup did not precede real library closure");
    }
    fs::remove_all(root);
}
