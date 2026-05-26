#pragma once

#include "api/ObeliskApi.h"
#include <string>
#include <vector>

namespace Obelisk::Core
{
    class PluginManager
    {
    public:
        static PluginManager& Get();

        void LoadPlugins(const std::string& directory);
        void UnloadAll();

    private:
        PluginManager();
        ~PluginManager();

        struct PluginInfo {
            std::string name;
            void* handle;
        };

        std::vector<PluginInfo> m_LoadedPlugins;
        ObeliskApi m_Api;
    };
}
