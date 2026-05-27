#include "PluginManager.h"
#include "EventManager.h"
#include "PluginConfig.h"
#include "hooks/ProcessEventHook.h"
#include "runtime/Logger.h"
#include <dlfcn.h>
#include <filesystem>
#include <algorithm>
#include <cstdlib>
#include <exception>
#include <vector>

namespace fs = std::filesystem;

namespace Obelisk::Core
{
    namespace
    {
        thread_local void* g_CurrentPluginOwner = nullptr;

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
    }

    // C-API Wrappers for Plugins
    extern "C" {
        void PluginLogInfo(const char* message) { OBELISK_INFO("[Plugin] {}", message ? message : ""); }
        void PluginLogWarn(const char* message) { OBELISK_WARN("[Plugin] {}", message ? message : ""); }
        void PluginLogError(const char* message) { OBELISK_ERROR("[Plugin] {}", message ? message : ""); }

        void PluginRegisterPreProcessEvent(OnProcessEventCallback callback) {
            EventManager::Get().RegisterPreProcessEventOwned(ResolveCallbackOwner(callback), callback);
        }
        void PluginRegisterPostProcessEvent(OnProcessEventCallback callback) {
            EventManager::Get().RegisterPostProcessEventOwned(ResolveCallbackOwner(callback), callback);
        }
        void PluginRegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            EventManager::Get().RegisterPreProcessEventForNameIndexOwned(ResolveCallbackOwner(callback), nameIndex, callback);
        }
        void PluginRegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
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
        : PluginManager(DefaultLoader())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader)
        : m_Loader(&loader)
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
        m_Api.capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;
    }

    PluginManager::~PluginManager()
    {
        UnloadAll();
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
                if (entry.is_regular_file() && entry.path().extension() == ".so")
                    plugins.push_back(entry.path());
            }

            std::sort(plugins.begin(), plugins.end());
            OBELISK_INFO("Scanning for plugins in {}. Found {} candidate(s).", directory, plugins.size());

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

                std::string symbolError;
                InitFunc initFunc = reinterpret_cast<InitFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_Init", symbolError));
                if (!initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError);
                    m_Loader->Close(handle);
                    continue;
                }

                symbolError.clear();
                GetInfoFunc getInfoFunc = reinterpret_cast<GetInfoFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_GetInfo", symbolError));
                if (!getInfoFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_GetInfo: {}. Unloading.", pluginName, symbolError);
                    m_Loader->Close(handle);
                    continue;
                }

                ShutdownFunc shutdownFunc = ResolveShutdownFunc(*m_Loader, handle, pluginName);

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
                    m_Loader->Close(handle);
                    continue;
                }

                PreparedPluginConfig preparedConfig;
                std::string configError;
                if (!PreparePluginConfig(metadata, configRoot, preparedConfig, configError))
                {
                    OBELISK_ERROR("Plugin {} metadata/config rejected: {}. Unloading.", pluginName, configError);
                    m_Loader->Close(handle);
                    continue;
                }

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
                void* previousOwner = g_CurrentPluginOwner;
                g_CurrentPluginOwner = pluginOwner;
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
                g_CurrentPluginOwner = previousOwner;

                if (initialized)
                {
                    OBELISK_INFO("Plugin {} initialized successfully.", pluginName);
                    m_LoadedPlugins.push_back({pluginName, handle, pluginOwner, shutdownFunc});
                }
                else
                {
                    OBELISK_ERROR("Plugin {} failed to initialize.", pluginName);
                    CallPluginShutdown(pluginName, shutdownFunc);
                    const size_t removed = EventManager::Get().UnregisterCallbacksForOwner(pluginOwner);
                    if (removed > 0)
                        OBELISK_WARN("Removed {} callback(s) registered by failed plugin {} before dlclose.", removed, pluginName);
                    m_Loader->Close(handle);
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
            const size_t removed = EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
            if (removed > 0)
                OBELISK_INFO("Removed {} callback(s) registered by plugin {} before dlclose.", removed, plugin.name);
            m_Loader->Close(plugin.handle);
        }
        m_LoadedPlugins.clear();
    }
}
