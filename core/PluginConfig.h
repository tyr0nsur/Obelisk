#pragma once

#include "api/ObeliskApi.h"

#include <filesystem>
#include <string>

namespace Obelisk::Core
{
    struct PreparedPluginConfig {
        std::filesystem::path directory;
        std::filesystem::path path;
    };

    bool PreparePluginConfig(const ObeliskPluginMetadata& metadata,
                             const std::filesystem::path& configRoot,
                             PreparedPluginConfig& prepared,
                             std::string& error);
}
