#pragma once

#include <filesystem>
#include <string>

namespace Obelisk::Runtime
{
    bool IsSafeMarkerComponent(const std::string& value);
    bool IsInstanceMarkerEnabled(const char* root, const char* instanceId, const char* markerName);
    bool IsEnvAndInstanceMarkerEnabled(const char* envVarName, const char* markerName);
    std::filesystem::path InstanceMarkerPath(const std::filesystem::path& root,
                                             const std::string& instanceId,
                                             const std::string& markerName);
}
