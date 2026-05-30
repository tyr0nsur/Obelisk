#include <nlohmann/json.hpp>
#include <obelisk/ObeliskApi.h>

#include <array>
#include <atomic>
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
    std::mutex g_ConfigMutex;
    bool g_Enabled = false;
    bool g_AuditEnabled = false;
    int g_LogLimit = 10;
    uint64_t g_EventKindMask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
    uint64_t g_OwnerToken = 0;
    uint64_t g_GameplayPolicyRegistrationId = 0;
    std::atomic<int> g_LoggedEvents{0};

    constexpr std::size_t kEventNameCount =
        static_cast<std::size_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX) + 1u;
    constexpr std::size_t kResourceNameCount =
        static_cast<std::size_t>(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM) + 1u;

    std::array<std::array<char, 48>, kEventNameCount> g_EventNames{};
    std::array<std::array<char, 32>, kResourceNameCount> g_ResourceNames{};

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": [],
    "policy_audit": {
        "enabled": false,
        "event_kind_mask": 255,
        "log_limit": 10
    }
})json";

    constexpr uint64_t EventKindMask(uint32_t eventKind)
    {
        return eventKind >= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN &&
                       eventKind <= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX
                   ? (1ull << (eventKind - 1u))
                   : 0;
    }

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

    bool IsSafeDescriptorChar(unsigned char ch)
    {
        return std::isalnum(ch) || ch == '_' || ch == '-';
    }

    template <std::size_t Size>
    void CopySanitizedDescriptorName(std::array<char, Size>& out, const char* input, const char* fallback)
    {
        out.fill('\0');
        const char* source = input && input[0] != '\0' ? input : fallback;
        std::size_t written = 0;
        for (std::size_t i = 0; source[i] != '\0' && written + 1 < Size; ++i)
        {
            const unsigned char ch = static_cast<unsigned char>(source[i]);
            out[written++] = IsSafeDescriptorChar(ch) ? static_cast<char>(ch) : '_';
        }
        out[written] = '\0';
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

    bool ReadUInt64(const json& object, const char* fieldName, uint64_t& out)
    {
        const auto value = object.find(fieldName);
        if (value == object.end() || !value->is_number_unsigned())
            return false;

        out = value->get<uint64_t>();
        return true;
    }

    bool LoadConfigDocument(const std::filesystem::path& path, json& config)
    {
        std::ifstream in(path);
        if (!in.is_open())
        {
            SafeLogError("[oPolicyAudit] Config not readable.");
            return false;
        }

        try
        {
            config = json::parse(in);
        }
        catch (const std::exception& e)
        {
            SafeLogError((std::string("[oPolicyAudit] Config parse failed: ") + e.what()).c_str());
            return false;
        }

        if (!config.is_object())
        {
            SafeLogError("[oPolicyAudit] Config root must be an object.");
            return false;
        }

        return true;
    }

    bool LoadConfig(const ObeliskPluginInitContext* context)
    {
        if (!context || context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            !context->config_path || context->config_path[0] == '\0')
        {
            SafeLogError("[oPolicyAudit] Invalid plugin init context.");
            return false;
        }

        const std::filesystem::path path = context->config_path;
        std::lock_guard<std::mutex> lock(g_ConfigMutex);

        json config;
        if (!LoadConfigDocument(path, config))
            return false;

        if (!config.contains("enabled") || !config["enabled"].is_boolean())
        {
            SafeLogError("[oPolicyAudit] Config field enabled must be boolean.");
            return false;
        }

        if (config.contains("instance_allowlist") && !IsSafeInstanceAllowlist(config["instance_allowlist"]))
        {
            SafeLogError("[oPolicyAudit] Config field instance_allowlist must be an array of safe instance ids.");
            return false;
        }

        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
        {
            SafeLogError("[oPolicyAudit] Config field allow_all_instances must be boolean.");
            return false;
        }

        if (!InstanceAllowed(config, context->instance_id))
        {
            g_Enabled = false;
            return true;
        }

        g_Enabled = config.value("enabled", false);

        const json policyAudit = config.value("policy_audit", json::object());
        if (!policyAudit.is_object())
        {
            SafeLogError("[oPolicyAudit] Config field policy_audit must be an object.");
            return false;
        }

        if (policyAudit.contains("enabled") && !policyAudit["enabled"].is_boolean())
        {
            SafeLogError("[oPolicyAudit] policy_audit.enabled must be boolean.");
            return false;
        }

        g_AuditEnabled = policyAudit.value("enabled", false);
        if (!g_AuditEnabled)
            return true;

        if (!policyAudit.contains("log_limit") || !policyAudit["log_limit"].is_number_integer())
        {
            SafeLogError("[oPolicyAudit] policy_audit.log_limit must be an integer.");
            return false;
        }

        g_LogLimit = policyAudit.value("log_limit", 10);
        if (g_LogLimit < 0)
            g_LogLimit = 0;

        if (!ReadUInt64(policyAudit, "event_kind_mask", g_EventKindMask))
        {
            SafeLogError("[oPolicyAudit] policy_audit.event_kind_mask must be an unsigned integer.");
            return false;
        }

        if (g_EventKindMask == 0 ||
            (g_EventKindMask & ~static_cast<uint64_t>(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL)) != 0)
        {
            SafeLogError("[oPolicyAudit] policy_audit.event_kind_mask contains no supported event kinds.");
            return false;
        }

        return true;
    }

    const char* FieldName(std::size_t field)
    {
        switch (field)
        {
        case OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE:
            return "return_value";
        case OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX:
            return "variant_index";
        case OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET:
            return "force_set";
        case OBELISK_GAMEPLAY_POLICY_FIELD_FORCE:
            return "force";
        case OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER:
            return "requested_by_player";
        case OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN:
            return "ignore_cooldown";
        default:
            return nullptr;
        }
    }

    void AppendToken(char* buffer, std::size_t bufferSize, const char* token)
    {
        if (!buffer || bufferSize == 0 || !token)
            return;

        const std::size_t current = std::strlen(buffer);
        if (current >= bufferSize - 1)
            return;

        std::snprintf(buffer + current, bufferSize - current, "%s%s", current == 0 ? "" : ",", token);
    }

    void BuildFieldList(uint64_t fieldMask, char* buffer, std::size_t bufferSize)
    {
        if (!buffer || bufferSize == 0)
            return;

        buffer[0] = '\0';
        for (std::size_t field = 0; field < OBELISK_GAMEPLAY_POLICY_FIELD_COUNT; ++field)
        {
            if ((fieldMask & (1ull << field)) == 0)
                continue;

            AppendToken(buffer, bufferSize, FieldName(field));
        }

        if (buffer[0] == '\0')
            std::snprintf(buffer, bufferSize, "none");
    }

    const char* EventName(uint32_t eventKind)
    {
        if (eventKind < g_EventNames.size() && g_EventNames[eventKind][0] != '\0')
            return g_EventNames[eventKind].data();
        return "unknown";
    }

    const char* ResourceName(uint32_t resourceKind)
    {
        if (resourceKind < g_ResourceNames.size() && g_ResourceNames[resourceKind][0] != '\0')
            return g_ResourceNames[resourceKind].data();
        return "unknown";
    }

    void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* userData) noexcept
    {
        (void)userData;

        if (!event ||
            event->abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION ||
            event->struct_size < sizeof(ObeliskGameplayPolicyEvent))
        {
            SafeLogInfo("[oPolicyAudit] Ignored malformed gameplay policy event.");
            return;
        }

        if ((EventKindMask(event->event_kind) & g_EventKindMask) == 0)
            return;

        const int current = g_LoggedEvents.fetch_add(1);
        if (current >= g_LogLimit)
            return;

        char fields[128]{};
        BuildFieldList(event->field_mask, fields, sizeof(fields));

        char message[256]{};
        std::snprintf(
            message,
            sizeof(message),
            "[oPolicyAudit] GameplayPolicyEvent event=%s resource=%s fields=%s",
            EventName(event->event_kind),
            ResourceName(event->resource_kind),
            fields);
        SafeLogInfo(message);
    }

    bool HasGameplayPolicyEventApi(const ObeliskApi* api)
    {
        const auto fieldAvailable = [api](std::size_t offset, std::size_t size) {
            return api && api->struct_size >= offset + size;
        };

        return api &&
               api->abi_version == OBELISK_API_ABI_VERSION &&
               fieldAvailable(offsetof(ObeliskApi, capabilities), sizeof(api->capabilities)) &&
               fieldAvailable(offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle),
                   sizeof(api->RegisterGameplayPolicyEventWithOwnerTokenHandle)) &&
               fieldAvailable(offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken),
                   sizeof(api->UnregisterGameplayPolicyEventWithOwnerToken)) &&
               fieldAvailable(offsetof(ObeliskApi, DescribeResourceKind),
                   sizeof(api->DescribeResourceKind)) &&
               fieldAvailable(offsetof(ObeliskApi, DescribeGameplayPolicyEventKind),
                   sizeof(api->DescribeGameplayPolicyEventKind)) &&
               (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
               (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) != 0 &&
               (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) != 0 &&
               api->RegisterGameplayPolicyEventWithOwnerTokenHandle &&
               api->UnregisterGameplayPolicyEventWithOwnerToken &&
               api->DescribeResourceKind &&
               api->DescribeGameplayPolicyEventKind;
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

    bool CacheDescriptorNames(const ObeliskApi* api)
    {
        if (!api)
            return false;

        for (auto& name : g_EventNames)
            CopySanitizedDescriptorName(name, nullptr, "unknown");
        for (auto& name : g_ResourceNames)
            CopySanitizedDescriptorName(name, nullptr, "unknown");

        for (uint32_t kind = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN;
             kind <= OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX;
             ++kind)
        {
            if ((g_EventKindMask & EventKindMask(kind)) == 0)
                continue;

            ObeliskGameplayPolicyEventDescriptor descriptor{};
            descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
            if (!api->DescribeGameplayPolicyEventKind(kind, &descriptor) ||
                descriptor.abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION ||
                descriptor.struct_size < sizeof(ObeliskGameplayPolicyEventDescriptor))
            {
                SafeLogError("[oPolicyAudit] Failed to describe configured gameplay policy event kind.");
                return false;
            }

            CopySanitizedDescriptorName(g_EventNames[kind], descriptor.stable_name, "unknown");
        }

        for (uint32_t kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
             kind <= OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
             ++kind)
        {
            ObeliskResourceKindDescriptor descriptor{};
            descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
            if (!api->DescribeResourceKind(kind, &descriptor) ||
                descriptor.abi_version != OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION ||
                descriptor.struct_size < sizeof(ObeliskResourceKindDescriptor))
            {
                SafeLogError("[oPolicyAudit] Failed to describe gameplay policy resource kind.");
                return false;
            }

            CopySanitizedDescriptorName(g_ResourceNames[kind], descriptor.stable_name, "unknown");
        }

        return true;
    }

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_Enabled = false;
        g_AuditEnabled = false;
        g_LogLimit = 10;
        g_EventKindMask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
        g_OwnerToken = 0;
        g_GameplayPolicyRegistrationId = 0;
        g_LoggedEvents.store(0);
        for (auto& name : g_EventNames)
            CopySanitizedDescriptorName(name, nullptr, "unknown");
        for (auto& name : g_ResourceNames)
            CopySanitizedDescriptorName(name, nullptr, "unknown");
    }

    void UnregisterGameplayPolicyCallback() noexcept
    {
        try
        {
            if (g_HasApi && g_GameplayPolicyRegistrationId != 0 && g_Api.UnregisterGameplayPolicyEventWithOwnerToken)
            {
                g_Api.UnregisterGameplayPolicyEventWithOwnerToken(g_OwnerToken, g_GameplayPolicyRegistrationId);
                g_GameplayPolicyRegistrationId = 0;
            }
        }
        catch (...)
        {
        }
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
        out->plugin_id = "oPolicyAudit";
        out->name = "oPolicyAudit";
        out->version = "0.1.0-rc.2";
        out->config_file = "config.json";
        out->default_config_json = kDefaultConfig;
        return true;
    }
    catch (...)
    {
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    try
    {
        if (!api || !context)
            return false;

        if (api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext))
        {
            SafeLogError(api, "[oPolicyAudit] Incompatible Obelisk API.");
            return false;
        }

        CopyApiPrefix(api);
        g_OwnerToken = context->plugin_owner_token;
        g_LoggedEvents.store(0);

        if (!LoadConfig(context))
        {
            ResetState();
            return false;
        }

        api->LogInfo("[oPolicyAudit] Loaded.");

        if (!g_Enabled)
        {
            api->LogInfo("[oPolicyAudit] Disabled by config.");
            return true;
        }

        if (!g_AuditEnabled)
        {
            api->LogInfo("[oPolicyAudit] Policy audit disabled by config.");
            return true;
        }

        if (context->plugin_owner_token == 0 || !HasGameplayPolicyEventApi(api))
        {
            api->LogError("[oPolicyAudit] Gameplay policy audit requires owner-token gameplay policy API and descriptors.");
            ResetState();
            return false;
        }

        if (!CacheDescriptorNames(api))
        {
            ResetState();
            return false;
        }

        g_GameplayPolicyRegistrationId = api->RegisterGameplayPolicyEventWithOwnerTokenHandle(
            context->plugin_owner_token,
            g_EventKindMask,
            OnGameplayPolicyEvent,
            &g_LoggedEvents);
        if (g_GameplayPolicyRegistrationId == 0)
        {
            api->LogError("[oPolicyAudit] Failed to register gameplay policy event callback.");
            ResetState();
            return false;
        }

        api->LogInfo("[oPolicyAudit] Registered gameplay policy audit callback.");
        return true;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oPolicyAudit] Init failed: ") + e.what()).c_str());
        UnregisterGameplayPolicyCallback();
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oPolicyAudit] Init failed with unknown exception.");
        UnregisterGameplayPolicyCallback();
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        UnregisterGameplayPolicyCallback();
        SafeLogInfo("[oPolicyAudit] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}
