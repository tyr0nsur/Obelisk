#include "RuntimeMarkers.h"

#include <cctype>
#include <system_error>

namespace Obelisk::Runtime
{
    bool IsSafeMarkerComponent(const std::string& value)
    {
        if (value.empty())
            return false;

        for (unsigned char ch : value)
        {
            if (std::isalnum(ch) || ch == '_' || ch == '-')
                continue;
            return false;
        }
        return true;
    }

    std::filesystem::path InstanceMarkerPath(const std::filesystem::path& root,
                                             const std::string& instanceId,
                                             const std::string& markerName)
    {
        return root / "state" / "instances" / instanceId / markerName;
    }

    bool IsInstanceMarkerEnabled(const char* root, const char* instanceId, const char* markerName)
    {
        if (!root || root[0] == '\0' || !instanceId || instanceId[0] == '\0' ||
            !markerName || markerName[0] == '\0')
        {
            return false;
        }

        const std::string instance(instanceId);
        const std::string marker(markerName);
        if (!IsSafeMarkerComponent(instance) || !IsSafeMarkerComponent(marker))
            return false;

        std::error_code ec;
        return std::filesystem::is_regular_file(InstanceMarkerPath(root, instance, marker), ec) && !ec;
    }
}
