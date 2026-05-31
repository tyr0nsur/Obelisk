#include <nlohmann/json.hpp>
#include <obelisk/ObeliskApi.h>

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <exception>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>

using json = nlohmann::json;

namespace
{
    ObeliskApi g_Api{};
    bool g_HasApi = false;
    std::mutex g_StateMutex;
    bool g_Enabled = false;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": [],
    "descriptor_catalog": {
        "enabled": false,
        "log_catalog": true
    }
})json";

    constexpr uint64_t kDescriptorCapabilityMask =
        OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS |
        OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;

    constexpr size_t kRequiredBaseApiSize = offsetof(ObeliskApi, capabilities) + sizeof(ObeliskApi::capabilities);

    bool IsStringArray(const json& value)
    {
        if (!value.is_array())
            return false;
        for (const auto& entry : value)
        {
            if (!entry.is_string())
                return false;
        }
        return true;
    }

    bool IsSafeInstanceId(const std::string& value)
    {
        if (value.empty())
            return false;
        for (const unsigned char ch : value)
        {
            if (std::isalnum(ch) || ch == '_' || ch == '-')
                continue;
            return false;
        }
        return true;
    }

    bool IsSafeInstanceAllowlist(const json& value)
    {
        if (!IsStringArray(value))
            return false;
        for (const auto& entry : value)
        {
            if (!IsSafeInstanceId(entry.get<std::string>()))
                return false;
        }
        return true;
    }

    bool InstanceAllowed(const json& config, const char* instanceId)
    {
        if (config.value("allow_all_instances", false))
            return true;

        const auto allowlist = config.find("instance_allowlist");
        if (allowlist == config.end() || allowlist->empty())
            return false;
        if (!IsSafeInstanceAllowlist(*allowlist))
            return false;

        const std::string current = instanceId ? instanceId : "";
        for (const auto& entry : *allowlist)
        {
            if (entry.get<std::string>() == current)
                return true;
        }
        return false;
    }

    void SafeLogInfo(const char* message) noexcept
    {
        try
        {
            if (g_HasApi && g_Api.LogInfo)
                g_Api.LogInfo(message);
        }
        catch (...)
        {
        }
    }

    void SafeLogError(const ObeliskApi* api, const char* message) noexcept
    {
        try
        {
            if (api && api->LogError)
                api->LogError(message);
        }
        catch (...)
        {
        }
    }

    void SafeLogError(const char* message) noexcept
    {
        try
        {
            if (g_HasApi && g_Api.LogError)
                g_Api.LogError(message);
        }
        catch (...)
        {
        }
    }

    bool LoadConfigDocument(const std::filesystem::path& path, json& config)
    {
        std::ifstream in(path);
        if (!in.is_open())
            return false;
        try
        {
            config = json::parse(in);
        }
        catch (...)
        {
            return false;
        }
        return config.is_object();
    }

    bool LoadConfig(const ObeliskPluginInitContext* context, bool& logCatalog)
    {
        if (!context || context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            !context->config_path || context->config_path[0] == '\0')
        {
            return false;
        }

        json config;
        if (!LoadConfigDocument(context->config_path, config))
            return false;
        if (!config.contains("enabled") || !config["enabled"].is_boolean())
            return false;
        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
            return false;
        if (config.contains("instance_allowlist") && !IsSafeInstanceAllowlist(config["instance_allowlist"]))
            return false;

        bool catalogEnabled = false;
        logCatalog = true;
        const auto catalog = config.find("descriptor_catalog");
        if (catalog != config.end())
        {
            if (!catalog->is_object())
                return false;
            if (catalog->contains("enabled") && !(*catalog)["enabled"].is_boolean())
                return false;
            if (catalog->contains("log_catalog") && !(*catalog)["log_catalog"].is_boolean())
                return false;
            catalogEnabled = catalog->value("enabled", false);
            logCatalog = catalog->value("log_catalog", true);
        }

        std::lock_guard<std::mutex> lock(g_StateMutex);
        g_Enabled = config.value("enabled", false) && catalogEnabled && InstanceAllowed(config, context->instance_id);
        return true;
    }

    constexpr uint64_t EventKindMask(uint32_t eventKind)
    {
        return eventKind >= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN &&
                       eventKind <= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX
                   ? (1ull << (eventKind - 1u))
                   : 0;
    }

    bool IsSafeDescriptorChar(unsigned char ch)
    {
        return std::isalnum(ch) || ch == '_' || ch == '-' || ch == '.';
    }

    template <std::size_t InSize>
    bool CopySanitizedDescriptorText(char (&out)[InSize], const char (&input)[InSize])
    {
        static_assert(InSize > 0);
        std::size_t i = 0;
        for (; i + 1 < InSize && input[i] != '\0'; ++i)
        {
            const unsigned char ch = static_cast<unsigned char>(input[i]);
            out[i] = IsSafeDescriptorChar(ch) ? static_cast<char>(ch) : '_';
        }
        if (i == InSize - 1 && input[i] != '\0')
            return false;
        out[i] = '\0';
        for (++i; i < InSize; ++i)
            out[i] = '\0';
        return out[0] != '\0';
    }

    bool HasDescriptorApi(const ObeliskApi* api)
    {
        const size_t requiredSize =
            offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
            sizeof(api->DescribeGameplayPolicyEventKind);
        return api && api->abi_version == OBELISK_API_ABI_VERSION &&
               api->struct_size >= requiredSize &&
               (api->capabilities & kDescriptorCapabilityMask) == kDescriptorCapabilityMask &&
               api->DescribeResourceKind &&
               api->DescribeGameplayPolicyEventKind;
    }

    bool HasBaseApiPrefix(const ObeliskApi* api)
    {
        return api &&
               api->abi_version == OBELISK_API_ABI_VERSION &&
               api->struct_size >= kRequiredBaseApiSize;
    }

    void CopyApiPrefix(const ObeliskApi* api)
    {
        g_Api = {};
        if (!api)
        {
            g_HasApi = false;
            return;
        }

        const size_t copySize = api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api);
        std::memcpy(&g_Api, api, copySize);
        g_HasApi = true;
    }

    bool DescribeResource(const ObeliskApi* api, uint32_t resourceKind, ObeliskResourceKindDescriptor& out)
    {
        out = {};
        out.struct_size = sizeof(ObeliskResourceKindDescriptor);
        if (!api->DescribeResourceKind(resourceKind, &out))
            return false;
        return out.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
               out.struct_size == sizeof(ObeliskResourceKindDescriptor) &&
               out.resource_kind == resourceKind &&
               (out.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY) != 0 &&
               (out.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY) != 0 &&
               (out.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP) != 0 &&
               CopySanitizedDescriptorText(out.stable_name, out.stable_name) &&
               CopySanitizedDescriptorText(out.display_name, out.display_name);
    }

    bool DescribeEvent(const ObeliskApi* api, uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor& out)
    {
        out = {};
        out.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (!api->DescribeGameplayPolicyEventKind(eventKind, &out))
            return false;
        return out.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
               out.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor) &&
               out.event_kind == eventKind &&
               out.event_kind_mask == EventKindMask(eventKind) &&
               out.resource_kind != OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN &&
               (out.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
               CopySanitizedDescriptorText(out.stable_name, out.stable_name) &&
               CopySanitizedDescriptorText(out.display_name, out.display_name);
    }

    void LogResource(const ObeliskResourceKindDescriptor& descriptor)
    {
        char buffer[256]{};
        std::snprintf(buffer,
                      sizeof(buffer),
                      "[oDescriptorCatalog] resource kind=%u stable=%s event_mask=0x%llx field_mask=0x%llx flags=0x%llx",
                      descriptor.resource_kind,
                      descriptor.stable_name,
                      static_cast<unsigned long long>(descriptor.supported_gameplay_policy_event_mask),
                      static_cast<unsigned long long>(descriptor.supported_gameplay_policy_field_mask),
                      static_cast<unsigned long long>(descriptor.flags));
        SafeLogInfo(buffer);
    }

    void LogEvent(const ObeliskGameplayPolicyEventDescriptor& descriptor)
    {
        char buffer[256]{};
        std::snprintf(buffer,
                      sizeof(buffer),
                      "[oDescriptorCatalog] event kind=%u stable=%s resource=%u event_mask=0x%llx field_mask=0x%llx flags=0x%llx",
                      descriptor.event_kind,
                      descriptor.stable_name,
                      descriptor.resource_kind,
                      static_cast<unsigned long long>(descriptor.event_kind_mask),
                      static_cast<unsigned long long>(descriptor.field_mask),
                      static_cast<unsigned long long>(descriptor.flags));
        SafeLogInfo(buffer);
    }

    bool BuildCatalog(const ObeliskApi* api, bool logCatalog)
    {
        ObeliskResourceKindDescriptor structure{};
        ObeliskResourceKindDescriptor inventory{};
        if (!DescribeResource(api, OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE, structure) ||
            !DescribeResource(api, OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM, inventory))
        {
            SafeLogError("[oDescriptorCatalog] Resource descriptor query failed.");
            return false;
        }

        if (logCatalog)
        {
            LogResource(structure);
            LogResource(inventory);
        }

        for (uint32_t eventKind = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN;
             eventKind <= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX;
             ++eventKind)
        {
            ObeliskGameplayPolicyEventDescriptor event{};
            if (!DescribeEvent(api, eventKind, event))
            {
                SafeLogError("[oDescriptorCatalog] Gameplay policy event descriptor query failed.");
                return false;
            }

            const ObeliskResourceKindDescriptor* resource = nullptr;
            if (event.resource_kind == structure.resource_kind)
                resource = &structure;
            else if (event.resource_kind == inventory.resource_kind)
                resource = &inventory;
            else
            {
                SafeLogError("[oDescriptorCatalog] Event descriptor referenced an unknown resource category.");
                return false;
            }

            if ((event.event_kind_mask & resource->supported_gameplay_policy_event_mask) != event.event_kind_mask ||
                (event.field_mask & resource->supported_gameplay_policy_field_mask) != event.field_mask)
            {
                SafeLogError("[oDescriptorCatalog] Event descriptor is outside its resource descriptor masks.");
                return false;
            }

            const uint64_t expectedBackingFlag =
                event.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE
                    ? OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED
                    : OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            if ((event.flags & expectedBackingFlag) == 0)
            {
                SafeLogError("[oDescriptorCatalog] Event descriptor backing flag does not match resource kind.");
                return false;
            }

            if (logCatalog)
                LogEvent(event);
        }

        SafeLogInfo("[oDescriptorCatalog] Descriptor catalog validated.");
        return true;
    }

    void ResetState()
    {
        std::lock_guard<std::mutex> lock(g_StateMutex);
        g_Api = {};
        g_HasApi = false;
        g_Enabled = false;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    try
    {
        if (!out)
            return false;
        out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        out->struct_size = sizeof(ObeliskPluginMetadata);
        out->plugin_id = "oDescriptorCatalog";
        out->name = "oDescriptorCatalog";
        out->version = "0.1.0";
        out->config_file = "config.json";
        out->default_config_json = kDefaultConfig;
        return true;
    }
    catch (...)
    {
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    try
    {
        ResetState();
        if (!HasBaseApiPrefix(api))
        {
            SafeLogError(api, "[oDescriptorCatalog] Incompatible Obelisk API.");
            return false;
        }

        bool logCatalog = true;
        if (!LoadConfig(context, logCatalog))
        {
            SafeLogError(api, "[oDescriptorCatalog] Invalid config or init context.");
            return false;
        }

        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            CopyApiPrefix(api);
        }

        if (!g_Enabled)
            return true;

        if (!HasDescriptorApi(api))
        {
            SafeLogError(api, "[oDescriptorCatalog] Descriptor API unavailable.");
            ResetState();
            return false;
        }

        const bool catalogBuilt = BuildCatalog(api, logCatalog);
        if (!catalogBuilt)
            ResetState();
        return catalogBuilt;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oDescriptorCatalog] Init failed: ") + e.what()).c_str());
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oDescriptorCatalog] Init failed with unknown exception.");
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        ResetState();
    }
    catch (...)
    {
    }
}
