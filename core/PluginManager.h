#pragma once

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
        ~PluginManager();

        void LoadPlugins(const std::string& directory);
        void UnloadAll();

    private:
        struct PluginInfo {
            std::string name;
            void* handle;
            void* owner;
            void (*shutdown)();
        };

        std::vector<PluginInfo> m_LoadedPlugins;
        ObeliskApi m_Api;
        LibraryLoader* m_Loader;
    };
}
