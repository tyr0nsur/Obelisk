#include "PluginManager.h"
#include "EventManager.h"
#include "PluginConfig.h"
#include "hooks/ProcessEventHook.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include <dlfcn.h>
#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <exception>
#include <string_view>
#include <unordered_set>
#include <vector>

namespace fs = std::filesystem;

namespace Obelisk::Core
{
    namespace
    {
        thread_local void* g_CurrentPluginOwner = nullptr;
        std::atomic<uint64_t> g_ApiCapabilities{OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS};

        using GetInfoFunc = bool(*)(ObeliskPluginMetadata*);
        using InitFunc = bool(*)(ObeliskApi*, const ObeliskPluginInitContext*);
        using ShutdownFunc = void(*)();

        class DlopenLibraryLoader final : public PluginManager::LibraryLoader
        {
        public:
            void* Open(const fs::path& path, std::string& error) override
            {
                dlerror();
                void* handle = dlopen(path.string().c_str(), RTLD_NOW | RTLD_LOCAL);
                if (!handle)
                    error = dlerror();
                return handle;
            }

            void* Resolve(void* handle, const char* symbolName, std::string& error) override
            {
                dlerror();
                void* symbol = dlsym(handle, symbolName);
                const char* symbolError = dlerror();
                if (symbolError || !symbol)
                    error = symbolError ? symbolError : "unknown dlsym error";
                return symbol;
            }

            void* GetSymbolOwner(void* handle, void* symbol) override
            {
                Dl_info symbolInfo{};
                if (dladdr(symbol, &symbolInfo) != 0 && symbolInfo.dli_fbase)
                    return symbolInfo.dli_fbase;
                return handle;
            }

            void Close(void* handle) override
            {
                dlclose(handle);
            }
        };

        DlopenLibraryLoader& DefaultLoader()
        {
            static DlopenLibraryLoader loader;
            return loader;
        }

        void* ResolveCallbackOwner(OnProcessEventCallback callback)
        {
            if (g_CurrentPluginOwner)
                return g_CurrentPluginOwner;

            if (!callback)
                return nullptr;

            Dl_info info{};
            if (dladdr(reinterpret_cast<void*>(callback), &info) == 0)
                return nullptr;

            return info.dli_fbase;
        }

        ShutdownFunc ResolveShutdownFunc(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            std::string error;
            ShutdownFunc shutdownFunc = reinterpret_cast<ShutdownFunc>(loader.Resolve(handle, "ObeliskPlugin_Shutdown", error));
            if (!shutdownFunc)
            {
                OBELISK_INFO("Plugin {} does not export ObeliskPlugin_Shutdown; unload will use callback owner cleanup only.", pluginName);
                return nullptr;
            }

            return shutdownFunc;
        }

        void CallPluginShutdown(const std::string& pluginName, ShutdownFunc shutdownFunc)
        {
            if (!shutdownFunc)
                return;

            try
            {
                shutdownFunc();
                OBELISK_INFO("Plugin {} shutdown completed.", pluginName);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Plugin {} threw during shutdown: {}", pluginName, e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Plugin {} threw an unknown exception during shutdown.", pluginName);
            }
        }

        void SafeCloseLibrary(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            if (!handle)
                return;

            try
            {
                loader.Close(handle);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Plugin {} threw while closing library handle: {}", pluginName, e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Plugin {} threw an unknown exception while closing library handle.", pluginName);
            }
        }

        bool AreGlobalProcessEventCallbacksAllowed()
        {
            const char* env = std::getenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
            if (!env || std::string_view(env) != "1")
                return false;

            const char* markerRoot = std::getenv("OBELISK_ROOT");
            const char* instanceId = std::getenv("OBELISK_INSTANCE_ID");
            return Runtime::IsInstanceMarkerEnabled(markerRoot, instanceId, "allow-global-process-event-callbacks");
        }

        uint64_t BuildApiCapabilities()
        {
            uint64_t capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;
            if (AreGlobalProcessEventCallbacksAllowed())
                capabilities |= OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS;
            return capabilities;
        }

        bool IsGlobalProcessEventCallbackCapabilityEnabled()
        {
            return (g_ApiCapabilities.load(std::memory_order_acquire) &
                    OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0;
        }

        bool ValidateProcessEventCallback(const char* apiName, OnProcessEventCallback callback)
        {
            if (callback)
                return true;

            OBELISK_WARN("{} rejected null callback.", apiName);
            return false;
        }

        bool ValidateFilteredProcessEventCallback(const char* apiName,
                                                  int32_t nameIndex,
                                                  OnProcessEventCallback callback)
        {
            if (!ValidateProcessEventCallback(apiName, callback))
                return false;
            if (nameIndex >= 0)
                return true;

            OBELISK_WARN("{} rejected invalid negative FName index {}.", apiName, nameIndex);
            return false;
        }

        template <typename Fn>
        class ScopeExit
        {
        public:
            explicit ScopeExit(Fn fn)
                : m_Fn(fn)
            {
            }

            ~ScopeExit()
            {
                if (m_Active)
                    m_Fn();
            }

            ScopeExit(const ScopeExit&) = delete;
            ScopeExit& operator=(const ScopeExit&) = delete;

            void Dismiss()
            {
                m_Active = false;
            }

        private:
            Fn m_Fn;
            bool m_Active = true;
        };

        template <typename Fn>
        ScopeExit<Fn> MakeScopeExit(Fn fn)
        {
            return ScopeExit<Fn>(fn);
        }
    }

    // C-API Wrappers for Plugins
    extern "C" {
        void PluginLogInfo(const char* message) { OBELISK_INFO("[Plugin] {}", message ? message : ""); }
        void PluginLogWarn(const char* message) { OBELISK_WARN("[Plugin] {}", message ? message : ""); }
        void PluginLogError(const char* message) { OBELISK_ERROR("[Plugin] {}", message ? message : ""); }

        void PluginRegisterPreProcessEvent(OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPreProcessEvent", callback))
                return;
            if (!IsGlobalProcessEventCallbackCapabilityEnabled())
            {
                OBELISK_WARN("Global PreProcessEvent callback rejected. Use RegisterPreProcessEventForNameIndex or enable allow-global-process-event-callbacks for a controlled debug window.");
                return;
            }
            EventManager::Get().RegisterPreProcessEventOwned(ResolveCallbackOwner(callback), callback);
        }
        void PluginRegisterPostProcessEvent(OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPostProcessEvent", callback))
                return;
            if (!IsGlobalProcessEventCallbackCapabilityEnabled())
            {
                OBELISK_WARN("Global PostProcessEvent callback rejected. Use RegisterPostProcessEventForNameIndex or enable allow-global-process-event-callbacks for a controlled debug window.");
                return;
            }
            EventManager::Get().RegisterPostProcessEventOwned(ResolveCallbackOwner(callback), callback);
        }
        void PluginRegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPreProcessEventForNameIndex", nameIndex, callback))
                return;
            EventManager::Get().RegisterPreProcessEventForNameIndexOwned(ResolveCallbackOwner(callback), nameIndex, callback);
        }
        void PluginRegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPostProcessEventForNameIndex", nameIndex, callback))
                return;
            EventManager::Get().RegisterPostProcessEventForNameIndexOwned(ResolveCallbackOwner(callback), nameIndex, callback);
        }
        void PluginCallProcessEvent(void* caller, void* function, void* parms) {
            Hooks::ProcessEventHook::CallOriginalProcessEvent(caller, function, parms);
        }
    }

    PluginManager& PluginManager::Get()
    {
        static PluginManager instance;
        return instance;
    }

    PluginManager::PluginManager()
        : PluginManager(DefaultLoader(), ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader)
        : PluginManager(loader, ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher)
        : m_Loader(&loader)
        , m_ChatDispatcher(&chatDispatcher)
    {
        m_Api.LogInfo = PluginLogInfo;
        m_Api.LogWarn = PluginLogWarn;
        m_Api.LogError = PluginLogError;
        m_Api.RegisterPreProcessEvent = PluginRegisterPreProcessEvent;
        m_Api.RegisterPostProcessEvent = PluginRegisterPostProcessEvent;
        m_Api.RegisterPreProcessEventForNameIndex = PluginRegisterPreProcessEventForNameIndex;
        m_Api.RegisterPostProcessEventForNameIndex = PluginRegisterPostProcessEventForNameIndex;
        m_Api.CallProcessEvent = PluginCallProcessEvent;
        m_Api.abi_version = OBELISK_API_ABI_VERSION;
        m_Api.struct_size = sizeof(ObeliskApi);
        m_Api.capabilities = BuildApiCapabilities();
        g_ApiCapabilities.store(m_Api.capabilities, std::memory_order_release);
    }

    uint64_t PluginManager::ApiCapabilitiesForTesting() const
    {
        return m_Api.capabilities;
    }

    PluginManager::~PluginManager()
    {
        UnloadAll();
    }

    void PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason)
    {
        const size_t eventRemoved = EventManager::Get().UnregisterCallbacksForOwner(owner);
        const size_t chatRemoved = m_ChatDispatcher->UnregisterCallbacksForOwner(owner);

        if (eventRemoved > 0)
            OBELISK_INFO("Removed {} ProcessEvent callback(s) registered by plugin {} {}.", eventRemoved, pluginName, reason);
        if (chatRemoved > 0)
            OBELISK_INFO("Removed {} chat callback(s) registered by plugin {} {}.", chatRemoved, pluginName, reason);
    }

    bool PluginManager::IsPluginIdLoaded(const std::string& pluginId) const
    {
        return std::any_of(m_LoadedPlugins.begin(), m_LoadedPlugins.end(),
            [&pluginId](const PluginInfo& plugin) {
                return plugin.pluginId == pluginId;
            });
    }

    void PluginManager::LoadPlugins(const std::string& directory)
    {
        try
        {
            const char* configRootEnv = std::getenv("OBELISK_CONFIG_DIR");
            if (!configRootEnv || configRootEnv[0] == '\0')
            {
                OBELISK_ERROR("OBELISK_CONFIG_DIR is required for plugin loading. Plugins will not be loaded.");
                return;
            }

            const fs::path configRoot = configRootEnv;
            const char* instanceIdEnv = std::getenv("OBELISK_INSTANCE_ID");
            const std::string instanceId = instanceIdEnv ? instanceIdEnv : "";

            if (!fs::exists(directory))
            {
                OBELISK_WARN("Plugin directory {} does not exist. Creating it...", directory);
                fs::create_directories(directory);
                return;
            }

            std::vector<fs::path> plugins;
            for (const auto& entry : fs::directory_iterator(directory))
            {
                if (entry.path().extension() != ".so")
                    continue;

                if (entry.is_symlink())
                {
                    OBELISK_WARN("Skipping plugin candidate {} because plugin symlinks are not allowed.", entry.path().filename().string());
                    continue;
                }

                if (entry.is_regular_file())
                    plugins.push_back(entry.path());
            }

            std::sort(plugins.begin(), plugins.end());
            OBELISK_INFO("Scanning for plugins in {}. Found {} candidate(s).", directory, plugins.size());

            std::unordered_set<std::string> pluginIds;
            for (const auto& path : plugins)
            {
                std::string pluginName = path.filename().string();

                OBELISK_INFO("Loading plugin: {}", pluginName);

                std::string loaderError;
                void* handle = m_Loader->Open(path, loaderError);
                if (!handle)
                {
                    OBELISK_ERROR("Failed to load plugin {}: {}", pluginName, loaderError);
                    continue;
                }

                auto handleCleanup = MakeScopeExit([&]() {
                    SafeCloseLibrary(*m_Loader, handle, pluginName);
                });

                std::string symbolError;
                GetInfoFunc getInfoFunc = reinterpret_cast<GetInfoFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_GetInfo", symbolError));
                if (!getInfoFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_GetInfo: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                ObeliskPluginMetadata metadata{};
                bool metadataLoaded = false;
                try
                {
                    metadataLoaded = getInfoFunc(&metadata);
                }
                catch (const std::exception& e)
                {
                    OBELISK_ERROR("Plugin {} threw while reporting metadata: {}", pluginName, e.what());
                }
                catch (...)
                {
                    OBELISK_ERROR("Plugin {} threw an unknown exception while reporting metadata.", pluginName);
                }

                if (!metadataLoaded)
                {
                    OBELISK_ERROR("Plugin {} failed to report metadata. Unloading.", pluginName);
                    continue;
                }

                PreparedPluginConfig preparedConfig;
                std::string configError;
                if (!PreparePluginConfig(metadata, configRoot, instanceId, preparedConfig, configError))
                {
                    OBELISK_ERROR("Plugin {} metadata/config rejected: {}. Unloading.", pluginName, configError);
                    continue;
                }

                if (!pluginIds.insert(metadata.plugin_id).second)
                {
                    OBELISK_ERROR("Plugin {} rejected: duplicate plugin_id '{}'. Unloading.", pluginName, metadata.plugin_id);
                    continue;
                }

                if (IsPluginIdLoaded(metadata.plugin_id))
                {
                    OBELISK_WARN("Plugin {} skipped because plugin_id '{}' is already loaded.", pluginName, metadata.plugin_id);
                    continue;
                }

                if (!preparedConfig.enabled)
                {
                    OBELISK_INFO("Plugin {} skipped because config enabled=false.", pluginName);
                    continue;
                }

                if (!preparedConfig.instance_allowed)
                {
                    OBELISK_INFO("Plugin {} skipped because instance '{}' is not in instance_allowlist.", pluginName, instanceId);
                    continue;
                }

                symbolError.clear();
                InitFunc initFunc = reinterpret_cast<InitFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_Init", symbolError));
                if (!initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                ShutdownFunc shutdownFunc = ResolveShutdownFunc(*m_Loader, handle, pluginName);

                const std::string configDir = preparedConfig.directory.string();
                const std::string configPath = preparedConfig.path.string();
                ObeliskPluginInitContext initContext{
                    OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION,
                    sizeof(ObeliskPluginInitContext),
                    configDir.c_str(),
                    configPath.c_str(),
                    instanceId.c_str()
                };

                void* pluginOwner = m_Loader->GetSymbolOwner(handle, reinterpret_cast<void*>(initFunc));
                if (!pluginOwner)
                    pluginOwner = handle;

                bool initialized = false;
                bool initAttempted = false;
                auto initCleanup = MakeScopeExit([&]() {
                    if (!initAttempted)
                        return;
                    CallPluginShutdown(pluginName, shutdownFunc);
                    UnregisterPluginCallbacks(pluginName, pluginOwner, "after init failure and before dlclose");
                });

                void* previousOwner = g_CurrentPluginOwner;
                g_CurrentPluginOwner = pluginOwner;
                auto ownerRestore = MakeScopeExit([&]() {
                    g_CurrentPluginOwner = previousOwner;
                });

                initAttempted = true;
                try
                {
                    initialized = initFunc(&m_Api, &initContext);
                }
                catch (const std::exception& e)
                {
                    OBELISK_ERROR("Plugin {} threw during initialization: {}", pluginName, e.what());
                }
                catch (...)
                {
                    OBELISK_ERROR("Plugin {} threw an unknown exception during initialization.", pluginName);
                }
                ownerRestore.Dismiss();
                g_CurrentPluginOwner = previousOwner;

                if (initialized)
                {
                    OBELISK_INFO("Plugin {} initialized successfully.", pluginName);
                    m_LoadedPlugins.push_back({pluginName, metadata.plugin_id, handle, pluginOwner, shutdownFunc});
                    initCleanup.Dismiss();
                    handleCleanup.Dismiss();
                }
                else
                {
                    OBELISK_ERROR("Plugin {} failed to initialize.", pluginName);
                }
            }
        }
        catch (const std::exception& e)
        {
            OBELISK_ERROR("Failed to load plugins from {}: {}", directory, e.what());
        }
        catch (...)
        {
            OBELISK_ERROR("Failed to load plugins from {}: unknown exception", directory);
        }
    }

    void PluginManager::UnloadAll()
    {
        for (auto it = m_LoadedPlugins.rbegin(); it != m_LoadedPlugins.rend(); ++it)
        {
            auto& plugin = *it;
            OBELISK_INFO("Unloading plugin: {}", plugin.name);
            CallPluginShutdown(plugin.name, plugin.shutdown);
            UnregisterPluginCallbacks(plugin.name, plugin.owner, "before dlclose");
            SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name);
        }
        m_LoadedPlugins.clear();
    }
}
