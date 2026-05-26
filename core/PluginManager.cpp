#include "PluginManager.h"
#include "EventManager.h"
#include "hooks/ProcessEventHook.h"
#include "runtime/Logger.h"
#include <dlfcn.h>
#include <filesystem>
#include <algorithm>
#include <exception>
#include <vector>

namespace fs = std::filesystem;

namespace Obelisk::Core
{
    namespace
    {
        thread_local void* g_CurrentPluginOwner = nullptr;

        using InitFunc = bool(*)(ObeliskApi*);
        using ShutdownFunc = void(*)();

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

        ShutdownFunc ResolveShutdownFunc(void* handle, const std::string& pluginName)
        {
            dlerror();
            ShutdownFunc shutdownFunc = reinterpret_cast<ShutdownFunc>(dlsym(handle, "ObeliskPlugin_Shutdown"));
            const char* symbolError = dlerror();
            if (symbolError || !shutdownFunc)
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
                std::string pluginPath = path.string();
                std::string pluginName = path.filename().string();

                OBELISK_INFO("Loading plugin: {}", pluginName);

                void* handle = dlopen(pluginPath.c_str(), RTLD_NOW | RTLD_LOCAL);
                if (!handle)
                {
                    OBELISK_ERROR("Failed to load plugin {}: {}", pluginName, dlerror());
                    continue;
                }

                dlerror();
                InitFunc initFunc = reinterpret_cast<InitFunc>(dlsym(handle, "ObeliskPlugin_Init"));
                const char* symbolError = dlerror();

                if (symbolError || !initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError ? symbolError : "unknown dlsym error");
                    dlclose(handle);
                    continue;
                }

                ShutdownFunc shutdownFunc = ResolveShutdownFunc(handle, pluginName);

                Dl_info initInfo{};
                void* pluginOwner = nullptr;
                if (dladdr(reinterpret_cast<void*>(initFunc), &initInfo) != 0)
                    pluginOwner = initInfo.dli_fbase;
                if (!pluginOwner)
                    pluginOwner = handle;

                bool initialized = false;
                void* previousOwner = g_CurrentPluginOwner;
                g_CurrentPluginOwner = pluginOwner;
                try
                {
                    initialized = initFunc(&m_Api);
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
                    dlclose(handle);
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
        for (auto& plugin : m_LoadedPlugins)
        {
            OBELISK_INFO("Unloading plugin: {}", plugin.name);
            CallPluginShutdown(plugin.name, plugin.shutdown);
            const size_t removed = EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
            if (removed > 0)
                OBELISK_INFO("Removed {} callback(s) registered by plugin {} before dlclose.", removed, plugin.name);
            dlclose(plugin.handle);
        }
        m_LoadedPlugins.clear();
    }
}
