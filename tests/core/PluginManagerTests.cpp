#include "core/EventManager.h"
#include "core/PluginManager.h"
#include "runtime/Logger.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace fs = std::filesystem;

namespace
{
    constexpr const char* kDefaultConfig =
        R"({"enabled":false,"instance_allowlist":["arkserver"]})";

    struct FakePlugin {
        std::string filename;
        std::string pluginId = "fake_plugin";
        bool hasGetInfo = true;
        bool hasInit = true;
        bool hasShutdown = true;
        bool getInfoResult = true;
        bool initResult = true;
        bool validMetadata = true;
        bool registerCallback = false;
        int getInfoCalls = 0;
        int initCalls = 0;
        int shutdownCalls = 0;
        int closeCalls = 0;
        std::string initConfigDir;
        std::string initConfigPath;
        std::string initInstanceId;
        void* owner = this;
    };

    FakePlugin* g_CurrentFakePlugin = nullptr;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool FakeCallback(void*, void*, void*)
    {
        return true;
    }

    bool FakeGetInfo(ObeliskPluginMetadata* out)
    {
        Require(g_CurrentFakePlugin != nullptr, "fake GetInfo called without current plugin");
        ++g_CurrentFakePlugin->getInfoCalls;
        if (!g_CurrentFakePlugin->getInfoResult)
            return false;

        const char* pluginId = g_CurrentFakePlugin->validMetadata
            ? g_CurrentFakePlugin->pluginId.c_str()
            : "../bad_plugin";

        *out = ObeliskPluginMetadata{
            OBELISK_PLUGIN_METADATA_ABI_VERSION,
            sizeof(ObeliskPluginMetadata),
            pluginId,
            "Fake Plugin",
            "1.0.0",
            "config.json",
            kDefaultConfig,
        };
        return true;
    }

    bool FakeInit(ObeliskApi* api, const ObeliskPluginInitContext* context)
    {
        Require(g_CurrentFakePlugin != nullptr, "fake Init called without current plugin");
        ++g_CurrentFakePlugin->initCalls;
        g_CurrentFakePlugin->initConfigDir = context->config_dir ? context->config_dir : "";
        g_CurrentFakePlugin->initConfigPath = context->config_path ? context->config_path : "";
        g_CurrentFakePlugin->initInstanceId = context->instance_id ? context->instance_id : "";

        Require(api != nullptr, "plugin init received null API");
        Require(api->abi_version == OBELISK_API_ABI_VERSION, "plugin init received wrong API ABI version");
        Require(api->struct_size == sizeof(ObeliskApi), "plugin init received wrong API struct size");
        Require((api->capabilities & OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS) != 0,
                "plugin init received API without owned callback capability");

        if (g_CurrentFakePlugin->registerCallback)
            api->RegisterPreProcessEvent(FakeCallback);

        return g_CurrentFakePlugin->initResult;
    }

    void FakeShutdown()
    {
        Require(g_CurrentFakePlugin != nullptr, "fake Shutdown called without current plugin");
        ++g_CurrentFakePlugin->shutdownCalls;
    }

    class FakeLoader final : public Obelisk::Core::PluginManager::LibraryLoader
    {
    public:
        void Add(FakePlugin& plugin)
        {
            m_Plugins.emplace(plugin.filename, &plugin);
        }

        void* Open(const fs::path& path, std::string& error) override
        {
            const auto it = m_Plugins.find(path.filename().string());
            if (it == m_Plugins.end())
            {
                error = "fake plugin not registered";
                return nullptr;
            }
            return it->second;
        }

        void* Resolve(void* handle, const char* symbolName, std::string& error) override
        {
            auto* plugin = static_cast<FakePlugin*>(handle);
            g_CurrentFakePlugin = plugin;

            const std::string symbol = symbolName ? symbolName : "";
            if (symbol == "ObeliskPlugin_GetInfo" && plugin->hasGetInfo)
                return reinterpret_cast<void*>(&FakeGetInfo);
            if (symbol == "ObeliskPlugin_Init" && plugin->hasInit)
                return reinterpret_cast<void*>(&FakeInit);
            if (symbol == "ObeliskPlugin_Shutdown" && plugin->hasShutdown)
                return reinterpret_cast<void*>(&FakeShutdown);

            error = "missing fake symbol " + symbol;
            return nullptr;
        }

        void* GetSymbolOwner(void* handle, void*) override
        {
            return static_cast<FakePlugin*>(handle)->owner;
        }

        void Close(void* handle) override
        {
            ++static_cast<FakePlugin*>(handle)->closeCalls;
        }

    private:
        std::unordered_map<std::string, FakePlugin*> m_Plugins;
    };

    fs::path MakeTempRoot(const char* name)
    {
        const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        fs::path root = fs::temp_directory_path() / (std::string(name) + "_" + std::to_string(now));
        fs::create_directories(root / "plugins");
        fs::create_directories(root / "config");
        return root;
    }

    void TouchPlugin(const fs::path& root, const std::string& filename)
    {
        std::ofstream out(root / "plugins" / filename);
        Require(out.is_open(), "failed to create fake plugin candidate");
    }

    void ConfigureEnvironment(const fs::path& root)
    {
        setenv("OBELISK_CONFIG_DIR", (root / "config").string().c_str(), 1);
        setenv("OBELISK_LOG_DIR", (root / "logs").string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
    }

    void CleanupPlugin(FakePlugin& plugin)
    {
        Obelisk::Core::EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
        g_CurrentFakePlugin = nullptr;
    }

    void TestValidPluginLoadsAndUnloadCleansCallbacks()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_valid");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "valid.so", .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "valid plugin GetInfo was not called once");
        Require(plugin.initCalls == 1, "valid plugin Init was not called once");
        Require(plugin.closeCalls == 0, "valid plugin was closed during load");
        Require(fs::exists(root / "config" / plugin.pluginId / "config.json"), "valid plugin config was not prepared");
        Require(plugin.initInstanceId == "arkserver", "instance id was not passed to plugin init");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback was not registered during plugin init");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "valid plugin shutdown was not called during unload");
        Require(plugin.closeCalls == 1, "valid plugin was not closed during unload");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback survived plugin unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMissingGetInfoRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_no_getinfo");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "missing_getinfo.so", .hasGetInfo = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 0, "plugin without GetInfo was initialized");
        Require(plugin.closeCalls == 1, "plugin without GetInfo was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMissingInitRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_no_init");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "missing_init.so", .hasInit = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 0, "plugin without Init reached GetInfo");
        Require(plugin.closeCalls == 1, "plugin without Init was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInvalidMetadataRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_bad_metadata");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "bad_metadata.so", .validMetadata = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "bad metadata plugin did not report metadata");
        Require(plugin.initCalls == 0, "bad metadata plugin was initialized");
        Require(plugin.closeCalls == 1, "bad metadata plugin was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitFailureCleansCallbacksAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_init_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "init_fail.so", .initResult = false, .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "init-failing plugin did not report metadata");
        Require(plugin.initCalls == 1, "init-failing plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-failing plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "init-failing plugin was not closed");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback registered by failed plugin survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }
}

int main()
{
    const fs::path logRoot = MakeTempRoot("obelisk_plugin_manager_logs");
    setenv("OBELISK_LOG_DIR", logRoot.string().c_str(), 1);
    Obelisk::Logger::Init();

    TestValidPluginLoadsAndUnloadCleansCallbacks();
    TestMissingGetInfoRejectsAndCloses();
    TestMissingInitRejectsAndCloses();
    TestInvalidMetadataRejectsAndCloses();
    TestInitFailureCleansCallbacksAndCloses();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "PluginManagerTests passed\n";
    return 0;
}
