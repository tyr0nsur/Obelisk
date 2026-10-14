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
    nlohmann::json Catalog(int64_t price = 25)
    {
        return {{"enabled", true}, {"allow_all_instances", false}, {"instance_allowlist", {"suite-test"}},
            {"catalog_revision", "catalog-v1"},
            {"shop", {{{"id", "starter"}, {"name", "Paquete inicial"}, {"description", "Materiales del catalogo."}, {"price", price}},
                      {{"id", "tools"}, {"name", "Herramientas"}, {"description", "Herramientas de ejemplo."}, {"price", 30}},
                      {{"id", "food"}, {"name", "Comida"}, {"description", "Comida de ejemplo."}, {"price", 5}},
                      {{"id", "armor"}, {"name", "Armadura"}, {"description", "Armadura de ejemplo."}, {"price", 50}}}},
            {"kits", {{{"id", "welcome"}, {"name", "Bienvenida"}, {"description", "Kit inicial configurable."},
                        {"max_claims", 1}, {"cooldown_seconds", 3600}}}}};
    }
    void Config(const fs::path& root, const nlohmann::json& value)
    { std::ofstream(root / "config/oShopKits/config.json") << value.dump(); }
    auto Deadline() { return std::chrono::steady_clock::now() + std::chrono::seconds(2); }
}

void TestNativeShopKitsPluginIntegration()
{
    const auto root = fs::temp_directory_path() /
        ("ObeliskShopKits_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directories(root / "plugins"); fs::create_directories(root / "config/oShopKits");
    Environment environment(root);
    ChatEventDispatcher chat; CommandDispatcher commands; PlayerLifecycleDispatcher lifecycle;
    commands.SetAvailable(true); NativeLoader loader(commands);
    {
        PluginManager manager(loader, chat, commands, lifecycle);
        manager.LoadPlugins((root / "plugins").string());
        fs::copy_file(OBELISK_SHOP_KITS_PLUGIN_PATH, root / "plugins/oShopKits.so"); Config(root, Catalog());
        Require(manager.ExecuteOperation("start", "oShopKits", Deadline())["ok"], "new shop plugin not discovered hot");
        Require(commands.SubscriptionCount() == 2, "catalog command registrations missing");
        int first, second; std::vector<Reply> replies;
        Require(commands.Dispatch(&first, "/SHOP starter", 0, Capture, &replies) == 1 &&
                replies.back().Controller == &first && replies.back().Text.find("25 puntos") != std::string::npos &&
                replies.back().Text.find("no estan disponibles") != std::string::npos, "shop detail misrouted or overstated fulfillment");
        Require(commands.Dispatch(&second, "/kits\tWELCOME", 0, Capture, &replies) == 1 &&
                replies.back().Controller == &second && replies.back().Text.find("3600 s") != std::string::npos,
                "kit info wrong or reply misrouted");
        Require(commands.Dispatch(&first, "/shop 2", 0, Capture, &replies) == 1 &&
                replies.back().Text.find("2/2") != std::string::npos && replies.back().Text.find("armor") != std::string::npos &&
                replies.back().Text.find("starter") == std::string::npos, "pagination inconsistent");
        for (const auto* input : {"/shop 0", "/shop 999999999999999999999999", "/shop bad topic", "/kits missing"})
            Require(commands.Dispatch(&first, input, 0, Capture, &replies) == 1 && replies.back().Text.size() <= 1024,
                    "invalid argument did not produce bounded response");
        Require(commands.Dispatch(&first, "/shopper", 0, Capture, &replies) == 0 &&
                commands.Dispatch(&first, "/buy starter", 0, Capture, &replies) == 0 &&
                commands.Dispatch(&first, "/kit welcome", 0, Capture, &replies) == 0,
                "prefix or unavailable purchase/fulfillment command was registered");
        Require(manager.ExecuteOperation("pause", "oShopKits", Deadline())["ok"] &&
                commands.SubscriptionCount() == 2 && commands.Dispatch(&first, "/shop", 0, Capture, &replies) == 0,
                "pause did not close admission while retaining catalog");
        Require(manager.ExecuteOperation("resume", "oShopKits", Deadline())["ok"], "shop resume failed");
        auto changed = Catalog(99); changed["shop"][0]["name"] = "Materiales espa\xc3\xb1oles"; Config(root, changed);
        Require(manager.ExecuteOperation("reload", "oShopKits", Deadline())["ok"] &&
                commands.Dispatch(&first, "/shop STARTER", 0, Capture, &replies) == 1 &&
                replies.back().Text.find("99 puntos") != std::string::npos &&
                replies.back().Text.find("espa\xc3\xb1oles") != std::string::npos, "reload did not publish UTF-8 catalog change");
        Require(manager.ExecuteOperation("stop", "oShopKits", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                "shop stop did not drain registrations");
        for (int invalid = 0; invalid < 5; ++invalid)
        {
            auto value = Catalog();
            if (invalid == 0) value["shop"][0]["price"] = -1;
            if (invalid == 1) value["shop"][0]["price"] = 1.5;
            if (invalid == 2) value["shop"].push_back(value["shop"][0]);
            if (invalid == 3) value["shop"][0]["description"] = std::string(257, 'x');
            if (invalid == 4) value["shop"][0]["unknown"] = true;
            Config(root, value);
            Require(!manager.ExecuteOperation("start", "oShopKits", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                    "invalid catalog activated partial registrations");
        }
        auto disabled = Catalog(); disabled["instance_allowlist"] = {"another-instance"}; Config(root, disabled);
        Require(!manager.ExecuteOperation("start", "oShopKits", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                "wrong instance activated catalog");
        { auto duplicate = Catalog().dump(); duplicate.insert(1, "\"enabled\":false,");
          std::ofstream(root / "config/oShopKits/config.json") << duplicate; }
        Require(!manager.ExecuteOperation("start", "oShopKits", Deadline())["ok"] && commands.SubscriptionCount() == 0,
                "duplicate config keys activated catalog");
        auto empty = Catalog(); empty["shop"] = nlohmann::json::array(); empty["kits"] = nlohmann::json::array(); Config(root, empty);
        Require(manager.ExecuteOperation("start", "oShopKits", Deadline())["ok"] &&
                commands.Dispatch(&first, "/shop", 0, Capture, &replies) == 1 &&
                replies.back().Text.find("No hay entradas") != std::string::npos, "empty catalog not honest");
        manager.UnloadAll(); Require(commands.SubscriptionCount() == 0 && loader.CleanBeforeClose,
                                     "catalog cleanup did not precede real dlclose");
    }
    fs::remove_all(root);
}
