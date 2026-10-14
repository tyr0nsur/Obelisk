#include "core/PluginManager.h"

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

    class NativeLoader final : public PluginManager::LibraryLoader
    {
    public:
        explicit NativeLoader(CommandDispatcher& dispatcher) : Commands(dispatcher) {}
        void* Open(const fs::path& path, std::string& error) override
        {
            auto* handle = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
            if (!handle) error = dlerror();
            return handle;
        }
        void* Resolve(void* handle, const char* name, std::string& error) override
        {
            auto* value = dlsym(handle, name); if (!value) error = "missing symbol"; return value;
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
        unsigned Closed = 0;
        bool CleanBeforeClose = true;
    };

    struct Reply { void* Controller; std::string Text; };
    bool Capture(void* controller, std::string_view text, void* data) noexcept
    {
        try { static_cast<std::vector<Reply>*>(data)->push_back({controller, std::string(text)}); return true; }
        catch (...) { return false; }
    }
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
            setenv("OBELISK_INSTANCE_ID", "suite-test", 1);
        }
        ~Environment()
        {
            for (const auto& value : Values)
                if (value.Present) setenv(value.Name, value.Text.c_str(), 1); else unsetenv(value.Name);
        }
    };
    void Config(const fs::path& root, std::string rules = "Normas: respeta a los demas.")
    {
        nlohmann::json value{{"enabled", true}, {"allow_all_instances", false},
            {"instance_allowlist", {"suite-test"}},
            {"texts", {{"help", "Ayuda"}, {"rules", rules}, {"motd", "Bienvenido"}, {"serverinfo", "Servidor"}}}};
        std::ofstream(root / "config/oEssentials/config.json") << value.dump();
    }
    auto Deadline() { return std::chrono::steady_clock::now() + std::chrono::seconds(2); }
}

void TestNativeEssentialsPluginIntegration()
{
    const auto root = fs::temp_directory_path() /
        ("ObeliskEssentials_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directories(root / "plugins"); fs::create_directories(root / "config/oEssentials");
    Environment environment(root);
    ChatEventDispatcher chat; CommandDispatcher commands; PlayerLifecycleDispatcher lifecycle;
    commands.SetAvailable(true);
    NativeLoader loader(commands);
    {
        PluginManager manager(loader, chat, commands, lifecycle);
        manager.LoadPlugins((root / "plugins").string());
        fs::create_symlink(OBELISK_ESSENTIALS_PLUGIN_PATH, root / "plugins/oEssentials.so"); Config(root);
        Require(!manager.ExecuteOperation("start", "oEssentials", Deadline())["ok"] &&
                commands.SubscriptionCount() == 0, "new plugin symlink was followed");
        fs::remove(root / "plugins/oEssentials.so");
        fs::remove_all(root / "config/oEssentials");
        fs::copy_file(OBELISK_ESSENTIALS_PLUGIN_PATH, root / "plugins/oWrongId.so");
        Require(!manager.ExecuteOperation("start", "oWrongId", Deadline())["ok"] &&
                commands.SubscriptionCount() == 0 && !fs::exists(root / "config/oEssentials"),
                "mismatched metadata identity activated or seeded another config");
        fs::remove(root / "plugins/oWrongId.so");
        fs::create_directory(root / "config/oEssentials");
        // Publishing after initial discovery must support a new safe ID without
        // restarting the runtime or invoking unrelated plugin constructors.
        fs::copy_file(OBELISK_ESSENTIALS_PLUGIN_PATH, root / "plugins/oEssentials.so"); Config(root);
        Require(!manager.ExecuteOperation("start", "../oEssentials", Deadline())["ok"], "path traversal start accepted");
        Require(!manager.ExecuteOperation("start", std::string(65, 'x'), Deadline())["ok"], "oversize ID accepted");
        Require(!manager.ExecuteOperation("start", "oEssentials", std::chrono::steady_clock::now())["ok"] &&
                commands.SubscriptionCount() == 0, "expired new plugin operation activated callbacks");
        Require(manager.ExecuteOperation("start", "oEssentials", Deadline())["ok"], "new plugin was not discovered hot");
        Require(commands.SubscriptionCount() == 4, "Essentials command registrations missing");
        int first, second; std::vector<Reply> replies;
        Require(commands.Dispatch(&first, "/HELP rules", 0, Capture, &replies) == 1 &&
                commands.Dispatch(&second, "/motd", 0, Capture, &replies) == 1,
                "real plugin did not accept mixed case, arguments or second origin");
        Require(replies.size() == 2 && replies[0].Controller == &first && replies[1].Controller == &second &&
                replies[0].Text == "Normas: respeta a los demas." && replies[1].Text == "Bienvenido",
                "real plugin response misrouted or wrong topic");
        Require(commands.Dispatch(&first, "/helpful", 0, Capture, &replies) == 0 &&
                commands.Dispatch(&first, "ordinary chat", 0, Capture, &replies) == 0,
                "prefix/ordinary chat was consumed");
        Require(commands.Dispatch(&first, "/help bad topic", 0, Capture, &replies) == 1 &&
                replies.back().Text.find("desconocido") != std::string::npos, "unknown topic was not handled safely");
        Require(manager.ExecuteOperation("pause", "oEssentials", Deadline())["ok"] &&
                commands.Dispatch(&first, "/rules", 0, Capture, &replies) == 0 && commands.SubscriptionCount() == 4,
                "pause discarded state or delivered a command");
        Require(manager.ExecuteOperation("resume", "oEssentials", Deadline())["ok"], "resume failed");
        Config(root, "Nuevas normas UTF-8: espa\xc3\xb1ol.");
        Require(manager.ExecuteOperation("reload", "oEssentials", Deadline())["ok"] &&
                commands.Dispatch(&first, "/help\t/RULES", 0, Capture, &replies) == 1 &&
                replies.back().Text == "Nuevas normas UTF-8: espa\xc3\xb1ol.", "reload did not preserve UTF-8/config semantics");
        Require(manager.ExecuteOperation("stop", "oEssentials", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                "stop did not drain registrations");
        Config(root, std::string(1025, 'x'));
        Require(!manager.ExecuteOperation("start", "oEssentials", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                "invalid text config activated partial commands");
        Config(root);
        Require(manager.ExecuteOperation("start", "oEssentials", Deadline())["ok"], "valid restart after bad config failed");
        manager.UnloadAll(); Require(commands.SubscriptionCount() == 0 && loader.CleanBeforeClose,
                                     "cleanup did not precede real dlclose");
    }
    fs::remove_all(root);
}
