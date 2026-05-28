#include "core/ChatEventDispatcher.h"
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
#include <vector>

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
        bool registerFilteredCallback = false;
        bool registerChatCallback = false;
        int getInfoCalls = 0;
        int initCalls = 0;
        int shutdownCalls = 0;
        int closeCalls = 0;
        std::string initConfigDir;
        std::string initConfigPath;
        std::string initInstanceId;
        void* owner = this;
        std::vector<std::string>* orderLog = nullptr;
        Obelisk::Core::ChatEventDispatcher* chatDispatcher = nullptr;
        size_t chatSubscriptionsAtClose = 0;
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

    void FakeChatCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
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

        if (g_CurrentFakePlugin->registerFilteredCallback)
            api->RegisterPreProcessEventForNameIndex(42, FakeCallback);

        if (g_CurrentFakePlugin->registerChatCallback)
        {
            Require(g_CurrentFakePlugin->chatDispatcher != nullptr,
                    "fake plugin requested chat callback without dispatcher");
            const uint64_t registrationId = g_CurrentFakePlugin->chatDispatcher->Register(
                g_CurrentFakePlugin->owner,
                Obelisk::Core::ChatMessageSubscription{FakeChatCallback, g_CurrentFakePlugin});
            Require(registrationId != 0, "fake chat callback registration failed");
        }

        if (g_CurrentFakePlugin->orderLog)
            g_CurrentFakePlugin->orderLog->push_back("init:" + g_CurrentFakePlugin->filename);

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
            auto* plugin = static_cast<FakePlugin*>(handle);
            if (plugin->chatDispatcher)
                plugin->chatSubscriptionsAtClose = plugin->chatDispatcher->SubscriptionCount();
            ++plugin->closeCalls;
            if (plugin->orderLog)
                plugin->orderLog->push_back("close:" + plugin->filename);
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

    void WritePluginConfig(const fs::path& root, const std::string& pluginId, const std::string& contents)
    {
        fs::create_directories(root / "config" / pluginId);
        std::ofstream out(root / "config" / pluginId / "config.json");
        Require(out.is_open(), "failed to create fake plugin config");
        out << contents;
        out.close();
        Require(static_cast<bool>(out), "failed to write fake plugin config");
    }

    void ConfigureEnvironment(const fs::path& root)
    {
        setenv("OBELISK_CONFIG_DIR", (root / "config").string().c_str(), 1);
        setenv("OBELISK_LOG_DIR", (root / "logs").string().c_str(), 1);
        setenv("OBELISK_MARKER_ROOT", root.string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
        unsetenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
    }

    void CleanupPlugin(FakePlugin& plugin)
    {
        Obelisk::Core::EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
        if (plugin.chatDispatcher)
            plugin.chatDispatcher->UnregisterCallbacksForOwner(plugin.owner);
        g_CurrentFakePlugin = nullptr;
    }

    void TestValidPluginLoadsAndUnloadCleansCallbacks()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_valid");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "valid.so", .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "valid plugin GetInfo was not called once");
        Require(plugin.initCalls == 1, "valid plugin Init was not called once");
        Require(plugin.closeCalls == 0, "valid plugin was closed during load");
        Require(fs::exists(root / "config" / plugin.pluginId / "config.json"), "valid plugin config was not prepared");
        Require(plugin.initInstanceId == "arkserver", "instance id was not passed to plugin init");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback was not registered during plugin init");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "owned chat callback was not registered during plugin init");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "valid plugin shutdown was not called during unload");
        Require(plugin.closeCalls == 1, "valid plugin was not closed during unload");
        Require(plugin.chatSubscriptionsAtClose == 0, "chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback survived plugin unload");
        Require(chatDispatcher.SubscriptionCount() == 0, "owned chat callback survived plugin unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGlobalProcessEventCallbackRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_denied");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "global_denied.so", .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) == 0,
                "global callback capability was enabled by default");

        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "global-denied plugin was not initialized");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global callback was registered without explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestFilteredProcessEventCallbackAllowedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_filtered_allowed");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "filtered_allowed.so", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "filtered callback was rejected by default");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGlobalProcessEventCallbackAllowedWithGate()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_allowed");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-global-process-event-callbacks");
        Require(marker.is_open(), "failed to create global callback marker");
        marker.close();

        FakePlugin plugin{.filename = "global_allowed.so", .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0,
                "global callback capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());

        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global callback was not registered with explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
        fs::remove_all(root);
    }

    void TestDisabledPluginPreparesConfigButDoesNotInit()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_disabled");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "disabled.so", .hasInit = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "disabled plugin metadata was not read");
        Require(plugin.initCalls == 0, "disabled plugin was initialized");
        Require(plugin.shutdownCalls == 0, "disabled plugin shutdown was called despite no init");
        Require(plugin.closeCalls == 1, "disabled plugin was not closed after skip");
        Require(fs::exists(root / "config" / plugin.pluginId / "config.json"),
                "disabled plugin default config was not prepared");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInstanceDisallowedPluginDoesNotInit()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_instance_disallowed");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "wrong_instance.so"};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver2"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "instance-disallowed plugin metadata was not read");
        Require(plugin.initCalls == 0, "instance-disallowed plugin was initialized");
        Require(plugin.closeCalls == 1, "instance-disallowed plugin was not closed after skip");

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
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

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
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "plugin without Init did not report metadata before rejection");
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
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "init-failing plugin did not report metadata");
        Require(plugin.initCalls == 1, "init-failing plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-failing plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "init-failing plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "failed plugin chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback registered by failed plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by failed plugin survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMultiplePluginsLoadSortedAndUnloadReverse()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_multi");
        ConfigureEnvironment(root);

        std::vector<std::string> orderLog;
        FakePlugin pluginA{.filename = "a_first.so", .pluginId = "plugin_a", .hasShutdown = false, .orderLog = &orderLog};
        FakePlugin pluginB{.filename = "b_second.so", .pluginId = "plugin_b", .hasShutdown = false, .orderLog = &orderLog};
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginB.filename);
        TouchPlugin(root, pluginA.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.UnloadAll();

        const std::vector<std::string> expected{
            "init:a_first.so",
            "init:b_second.so",
            "close:b_second.so",
            "close:a_first.so",
        };
        Require(orderLog == expected, "plugins were not loaded sorted and unloaded in reverse load order");
        Require(pluginA.closeCalls == 1, "first plugin was not closed once");
        Require(pluginB.closeCalls == 1, "second plugin was not closed once");

        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
        fs::remove_all(root);
    }

    void TestDuplicatePluginIdRejectsSecondPlugin()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_duplicate_id");
        ConfigureEnvironment(root);

        FakePlugin pluginA{.filename = "a_first.so", .pluginId = "duplicate"};
        FakePlugin pluginB{.filename = "b_second.so", .pluginId = "duplicate"};
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginA.filename);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, "duplicate", R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(pluginA.initCalls == 1, "first duplicate-id plugin was not initialized");
        Require(pluginB.getInfoCalls == 1, "second duplicate-id plugin metadata was not read");
        Require(pluginB.initCalls == 0, "second duplicate-id plugin was initialized");
        Require(pluginB.closeCalls == 1, "second duplicate-id plugin was not closed");

        manager.UnloadAll();
        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
        fs::remove_all(root);
    }

    void TestLoadPluginsSkipsAlreadyLoadedPluginId()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_idempotent");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "idempotent.so", .pluginId = "idempotent_plugin", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 2, "already-loaded plugin metadata was not checked on reload");
        Require(plugin.initCalls == 1, "already-loaded plugin was initialized more than once");
        Require(plugin.closeCalls == 1, "already-loaded duplicate handle was not closed during reload");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback from first loaded plugin was removed during reload");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "idempotent plugin shutdown was not called once");
        Require(plugin.closeCalls == 2, "loaded plugin handle was not closed during unload");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback from idempotent plugin survived unload");

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
    TestGlobalProcessEventCallbackRejectedByDefault();
    TestFilteredProcessEventCallbackAllowedByDefault();
    TestGlobalProcessEventCallbackAllowedWithGate();
    TestDisabledPluginPreparesConfigButDoesNotInit();
    TestInstanceDisallowedPluginDoesNotInit();
    TestMissingGetInfoRejectsAndCloses();
    TestMissingInitRejectsAndCloses();
    TestInvalidMetadataRejectsAndCloses();
    TestInitFailureCleansCallbacksAndCloses();
    TestMultiplePluginsLoadSortedAndUnloadReverse();
    TestDuplicatePluginIdRejectsSecondPlugin();
    TestLoadPluginsSkipsAlreadyLoadedPluginId();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "PluginManagerTests passed\n";
    return 0;
}
