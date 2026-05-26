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
    // C-API Wrappers for Plugins
    extern "C" {
        void PluginLogInfo(const char* message) { OBELISK_INFO("[Plugin] {}", message ? message : ""); }
        void PluginLogWarn(const char* message) { OBELISK_WARN("[Plugin] {}", message ? message : ""); }
        void PluginLogError(const char* message) { OBELISK_ERROR("[Plugin] {}", message ? message : ""); }

        void PluginRegisterPreProcessEvent(OnProcessEventCallback callback) {
            EventManager::Get().RegisterPreProcessEvent(callback);
        }
        void PluginRegisterPostProcessEvent(OnProcessEventCallback callback) {
            EventManager::Get().RegisterPostProcessEvent(callback);
        }
        void PluginRegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            EventManager::Get().RegisterPreProcessEventForNameIndex(nameIndex, callback);
        }
        void PluginRegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            EventManager::Get().RegisterPostProcessEventForNameIndex(nameIndex, callback);
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

                using InitFunc = bool(*)(ObeliskApi*);
                dlerror();
                InitFunc initFunc = reinterpret_cast<InitFunc>(dlsym(handle, "ObeliskPlugin_Init"));
                const char* symbolError = dlerror();

                if (symbolError || !initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError ? symbolError : "unknown dlsym error");
                    dlclose(handle);
                    continue;
                }

                bool initialized = false;
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

                if (initialized)
                {
                    OBELISK_INFO("Plugin {} initialized successfully.", pluginName);
                    m_LoadedPlugins.push_back({pluginName, handle});
                }
                else
                {
                    OBELISK_ERROR("Plugin {} failed to initialize.", pluginName);
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
            dlclose(plugin.handle);
        }
        m_LoadedPlugins.clear();
    }
}
