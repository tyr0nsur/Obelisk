#pragma once

#include "api/ObeliskApi.h"

#include <filesystem>
#include <string>

namespace Obelisk::Core
{
    struct PreparedPluginConfig {
        std::filesystem::path directory;
        std::filesystem::path path;
        bool enabled = false;
        bool instance_allowed = true;
    };

    bool PreparePluginConfig(const ObeliskPluginMetadata& metadata,
                             const std::filesystem::path& configRoot,
                             const std::string& instanceId,
                             PreparedPluginConfig& prepared,
                             std::string& error);

    bool IsSafeInstanceId(const std::string& value);
}
