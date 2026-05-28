#pragma once

#include "ChatEventDispatcher.h"
#include "api/ObeliskApi.h"
#include <filesystem>
#include <string>
#include <vector>

namespace Obelisk::Core
{
    class PluginManager
    {
    public:
        struct LibraryLoader {
            virtual ~LibraryLoader() = default;
            virtual void* Open(const std::filesystem::path& path, std::string& error) = 0;
            virtual void* Resolve(void* handle, const char* symbolName, std::string& error) = 0;
            virtual void* GetSymbolOwner(void* handle, void* symbol) = 0;
            virtual void Close(void* handle) = 0;
        };

        static PluginManager& Get();

        PluginManager();
        explicit PluginManager(LibraryLoader& loader);
        PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher);
        ~PluginManager();

        void LoadPlugins(const std::string& directory);
        void UnloadAll();

    private:
        struct PluginInfo {
            std::string name;
            std::string pluginId;
            void* handle;
            void* owner;
            void (*shutdown)();
        };

        std::vector<PluginInfo> m_LoadedPlugins;
        ObeliskApi m_Api;
        LibraryLoader* m_Loader;
        ChatEventDispatcher* m_ChatDispatcher;

        void UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason);
        bool IsPluginIdLoaded(const std::string& pluginId) const;
    };
}
