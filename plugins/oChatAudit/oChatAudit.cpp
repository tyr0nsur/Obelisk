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
    struct Config
    {
        bool runtimeEnabled = false;
        bool auditEnabled = false;
        uint64_t digestIntervalMs = 60000;
        bool logOnShutdown = true;
        uint64_t maxMessageSizeBucket = 4096;
    };

    struct Counters
    {
        uint64_t accepted = 0;
        uint64_t malformed = 0;
        uint64_t totalBytes = 0;
        uint64_t maxBytes = 0;
        uint64_t bucketOverflows = 0;
        std::array<uint64_t, OBELISK_CHAT_SEND_MODE_COUNT> modeCounts{};
        std::array<uint64_t, 5> sizeBuckets{};
    };

    ObeliskApi g_Api{};
    bool g_HasApi = false;
    std::mutex g_StateMutex;
    Config g_Config{};
    Counters g_Counters{};
    uint64_t g_OwnerToken = 0;
    uint64_t g_ChatRegistrationId = 0;
    std::atomic<uint64_t> g_TimerId{0};
    uint64_t g_UserData = 0xC0A701;

    constexpr size_t kRequiredBaseApiSize = offsetof(ObeliskApi, capabilities) + sizeof(ObeliskApi::capabilities);

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": [],
    "chat_audit": {
        "enabled": false,
        "digest_interval_ms": 60000,
        "log_on_shutdown": true,
        "max_message_size_bucket": 4096
    }
})json";

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
            void (*logInfo)(const char*) = nullptr;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                if (g_HasApi)
                    logInfo = g_Api.LogInfo;
            }
            if (logInfo)
                logInfo(message);
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
            void (*logError)(const char*) = nullptr;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                if (g_HasApi)
                    logError = g_Api.LogError;
            }
            if (logError)
                logError(message);
        }
        catch (...)
        {
        }
    }

    bool ReadPositiveBoundedUInt64(const json& object,
                                   const char* fieldName,
                                   uint64_t minValue,
                                   uint64_t maxValue,
                                   uint64_t& out)
    {
        const auto value = object.find(fieldName);
        if (value == object.end() || !value->is_number_unsigned())
            return false;

        const uint64_t parsed = value->get<uint64_t>();
        if (parsed < minValue || parsed > maxValue)
            return false;

        out = parsed;
        return true;
    }

    bool LoadConfigDocument(const std::filesystem::path& path, json& config)
    {
        std::ifstream in(path);
        if (!in.is_open())
        {
            SafeLogError("[oChatAudit] Config not readable.");
            return false;
        }

        try
        {
            config = json::parse(in);
        }
        catch (const std::exception& e)
        {
            SafeLogError((std::string("[oChatAudit] Config parse failed: ") + e.what()).c_str());
            return false;
        }

        if (!config.is_object())
        {
            SafeLogError("[oChatAudit] Config root must be an object.");
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
            SafeLogError("[oChatAudit] Invalid plugin init context.");
            return false;
        }

        json config;
        if (!LoadConfigDocument(std::filesystem::path(context->config_path), config))
            return false;

        if (!config.contains("enabled") || !config["enabled"].is_boolean())
        {
            SafeLogError("[oChatAudit] Config field enabled must be boolean.");
            return false;
        }

        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
        {
            SafeLogError("[oChatAudit] Config field allow_all_instances must be boolean.");
            return false;
        }

        if (config.contains("instance_allowlist") && !IsSafeInstanceAllowlist(config["instance_allowlist"]))
        {
            SafeLogError("[oChatAudit] Config field instance_allowlist must be an array of safe instance ids.");
            return false;
        }

        Config parsed{};
        parsed.runtimeEnabled = config.value("enabled", false) && InstanceAllowed(config, context->instance_id);

        const json chatAudit = config.value("chat_audit", json::object());
        if (!chatAudit.is_object())
        {
            SafeLogError("[oChatAudit] Config field chat_audit must be an object.");
            return false;
        }

        if (chatAudit.contains("enabled") && !chatAudit["enabled"].is_boolean())
        {
            SafeLogError("[oChatAudit] chat_audit.enabled must be boolean.");
            return false;
        }
        parsed.auditEnabled = chatAudit.value("enabled", false);

        if (chatAudit.contains("log_on_shutdown") && !chatAudit["log_on_shutdown"].is_boolean())
        {
            SafeLogError("[oChatAudit] chat_audit.log_on_shutdown must be boolean.");
            return false;
        }
        parsed.logOnShutdown = chatAudit.value("log_on_shutdown", true);

        if (!ReadPositiveBoundedUInt64(
                chatAudit,
                "max_message_size_bucket",
                1,
                1024 * 1024,
                parsed.maxMessageSizeBucket))
        {
            SafeLogError("[oChatAudit] chat_audit.max_message_size_bucket must be a bounded positive integer.");
            return false;
        }

        if (parsed.runtimeEnabled && parsed.auditEnabled &&
            !ReadPositiveBoundedUInt64(chatAudit, "digest_interval_ms", 1000, 24ull * 60ull * 60ull * 1000ull, parsed.digestIntervalMs))
        {
            SafeLogError("[oChatAudit] chat_audit.digest_interval_ms must be a bounded positive integer.");
            return false;
        }

        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            g_Config = parsed;
            g_Counters = {};
        }
        return true;
    }

    bool HasChatApi(const ObeliskApi* api)
    {
        return api &&
            api->abi_version == OBELISK_API_ABI_VERSION &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
                sizeof(api->UnregisterChatMessageEventWithOwnerToken) &&
            (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
            api->RegisterChatMessageEventWithOwnerTokenHandle &&
            api->UnregisterChatMessageEventWithOwnerToken;
    }

    bool HasTimerApi(const ObeliskApi* api)
    {
        return api &&
            api->abi_version == OBELISK_API_ABI_VERSION &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) +
                sizeof(api->UnregisterTimerWithOwnerToken) &&
            (api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0 &&
            api->RegisterTimerWithOwnerTokenHandle &&
            api->UnregisterTimerWithOwnerToken;
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

    std::size_t SizeBucket(uint64_t size, uint64_t maxBucket)
    {
        if (size == 0)
            return 0;
        if (size <= 64)
            return 1;
        if (size <= 512)
            return 2;
        if (size <= maxBucket)
            return 3;
        return 4;
    }

    void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* userData) noexcept
    {
        try
        {
            if (userData != &g_UserData)
                return;

            bool valid = false;
            uint32_t sendMode = 0;
            uint64_t messageSize = 0;
            uint64_t maxBucket = 4096;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                maxBucket = g_Config.maxMessageSizeBucket;
            }

            if (event &&
                event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION &&
                event->struct_size >= sizeof(ObeliskChatMessageEvent) &&
                event->send_mode <= OBELISK_CHAT_SEND_MODE_MAX &&
                (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
                event->sequence != 0 &&
                (event->message.data != nullptr || event->message.size == 0))
            {
                valid = true;
                sendMode = event->send_mode;
                messageSize = static_cast<uint64_t>(event->message.size);
            }

            std::lock_guard<std::mutex> lock(g_StateMutex);
            if (!valid)
            {
                ++g_Counters.malformed;
                return;
            }

            ++g_Counters.accepted;
            ++g_Counters.modeCounts[sendMode];
            g_Counters.totalBytes += messageSize;
            if (messageSize > g_Counters.maxBytes)
                g_Counters.maxBytes = messageSize;
            ++g_Counters.sizeBuckets[SizeBucket(messageSize, maxBucket)];
            if (messageSize > maxBucket)
                ++g_Counters.bucketOverflows;
        }
        catch (...)
        {
        }
    }

    Counters SnapshotAndResetCounters()
    {
        std::lock_guard<std::mutex> lock(g_StateMutex);
        Counters snapshot = g_Counters;
        g_Counters = {};
        return snapshot;
    }

    void EmitDigest(const Counters& counters, const char* reason) noexcept
    {
        try
        {
            char buffer[512]{};
            std::snprintf(
                buffer,
                sizeof(buffer),
                "[oChatAudit] digest reason=%s accepted=%llu malformed=%llu bytes_total=%llu bytes_max=%llu "
                "modes={global:%llu,tribe:%llu,local:%llu,alliance:%llu} "
                "size_buckets={empty:%llu,le64:%llu,le512:%llu,le_config:%llu,gt_config:%llu} bucket_overflows=%llu",
                reason ? reason : "timer",
                static_cast<unsigned long long>(counters.accepted),
                static_cast<unsigned long long>(counters.malformed),
                static_cast<unsigned long long>(counters.totalBytes),
                static_cast<unsigned long long>(counters.maxBytes),
                static_cast<unsigned long long>(counters.modeCounts[OBELISK_CHAT_SEND_MODE_GLOBAL]),
                static_cast<unsigned long long>(counters.modeCounts[OBELISK_CHAT_SEND_MODE_TRIBE]),
                static_cast<unsigned long long>(counters.modeCounts[OBELISK_CHAT_SEND_MODE_LOCAL]),
                static_cast<unsigned long long>(counters.modeCounts[OBELISK_CHAT_SEND_MODE_ALLIANCE]),
                static_cast<unsigned long long>(counters.sizeBuckets[0]),
                static_cast<unsigned long long>(counters.sizeBuckets[1]),
                static_cast<unsigned long long>(counters.sizeBuckets[2]),
                static_cast<unsigned long long>(counters.sizeBuckets[3]),
                static_cast<unsigned long long>(counters.sizeBuckets[4]),
                static_cast<unsigned long long>(counters.bucketOverflows));
            SafeLogInfo(buffer);
        }
        catch (...)
        {
        }
    }

    void HandleDigestTick(uint64_t timerId, void* userData) noexcept
    {
        if (userData != &g_UserData || timerId != g_TimerId.load(std::memory_order_acquire))
            return;
        EmitDigest(SnapshotAndResetCounters(), "timer");
    }

    void UnregisterDigestHandle() noexcept
    {
        try
        {
            bool (*unregisterTimer)(uint64_t, uint64_t) = nullptr;
            uint64_t ownerToken = 0;
            const uint64_t timerId = g_TimerId.exchange(0, std::memory_order_acq_rel);
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                if (g_HasApi && timerId != 0)
                {
                    unregisterTimer = g_Api.UnregisterTimerWithOwnerToken;
                    ownerToken = g_OwnerToken;
                }
            }
            if (unregisterTimer)
                unregisterTimer(ownerToken, timerId);
        }
        catch (...)
        {
        }
    }

    void UnregisterChat() noexcept
    {
        try
        {
            bool (*unregisterChat)(uint64_t, uint64_t) = nullptr;
            uint64_t ownerToken = 0;
            uint64_t registrationId = 0;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                registrationId = g_ChatRegistrationId;
                g_ChatRegistrationId = 0;
                if (g_HasApi && registrationId != 0)
                {
                    unregisterChat = g_Api.UnregisterChatMessageEventWithOwnerToken;
                    ownerToken = g_OwnerToken;
                }
            }
            if (unregisterChat)
                unregisterChat(ownerToken, registrationId);
        }
        catch (...)
        {
        }
    }

    void ResetState()
    {
        std::lock_guard<std::mutex> lock(g_StateMutex);
        g_Api = {};
        g_HasApi = false;
        g_Config = {};
        g_Counters = {};
        g_OwnerToken = 0;
        g_ChatRegistrationId = 0;
        g_TimerId.store(0, std::memory_order_release);
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
        out->plugin_id = "oChatAudit";
        out->name = "oChatAudit";
        out->version = "0.1.0-experimental";
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
        if (!api || !context)
            return false;

        if (api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < kRequiredBaseApiSize ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            context->plugin_owner_token == 0)
        {
            SafeLogError(api, "[oChatAudit] Incompatible Obelisk API.");
            return false;
        }

        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            CopyApiPrefix(api);
            g_OwnerToken = context->plugin_owner_token;
            g_ChatRegistrationId = 0;
            g_TimerId.store(0, std::memory_order_release);
            g_Counters = {};
        }

        if (!LoadConfig(context))
        {
            ResetState();
            return false;
        }

        SafeLogInfo("[oChatAudit] Loaded.");

        bool shouldRegister = false;
        uint64_t digestIntervalMs = 0;
        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            shouldRegister = g_Config.runtimeEnabled && g_Config.auditEnabled;
            digestIntervalMs = g_Config.digestIntervalMs;
        }

        if (!shouldRegister)
        {
            SafeLogInfo("[oChatAudit] Disabled by config.");
            return true;
        }

        if (!HasChatApi(api))
        {
            SafeLogError(api, "[oChatAudit] ChatMessageEvent API is not available.");
            ResetState();
            return false;
        }

        if (!HasTimerApi(api))
        {
            SafeLogError(api, "[oChatAudit] Timer API is not available.");
            ResetState();
            return false;
        }

        const uint64_t chatRegistrationId = api->RegisterChatMessageEventWithOwnerTokenHandle(
            context->plugin_owner_token,
            OnChatMessageEvent,
            &g_UserData);
        if (chatRegistrationId == 0)
        {
            SafeLogError(api, "[oChatAudit] Failed to register ChatMessageEvent callback.");
            ResetState();
            return false;
        }
        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            g_ChatRegistrationId = chatRegistrationId;
        }

        const uint64_t timerId = api->RegisterTimerWithOwnerTokenHandle(
            context->plugin_owner_token,
            digestIntervalMs,
            digestIntervalMs,
            OBELISK_TIMER_FLAG_REPEATING,
            HandleDigestTick,
            &g_UserData);
        if (timerId == 0)
        {
            SafeLogError(api, "[oChatAudit] Failed to register digest timer.");
            UnregisterChat();
            ResetState();
            return false;
        }
        g_TimerId.store(timerId, std::memory_order_release);

        SafeLogInfo("[oChatAudit] Registered chat audit callback and digest timer.");
        return true;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oChatAudit] Init failed: ") + e.what()).c_str());
        UnregisterDigestHandle();
        UnregisterChat();
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oChatAudit] Init failed with unknown exception.");
        UnregisterDigestHandle();
        UnregisterChat();
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        bool logOnShutdown = false;
        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            logOnShutdown = g_HasApi && g_Config.runtimeEnabled && g_Config.auditEnabled && g_Config.logOnShutdown;
        }

        UnregisterDigestHandle();
        UnregisterChat();

        if (logOnShutdown)
            EmitDigest(SnapshotAndResetCounters(), "shutdown");

        SafeLogInfo("[oChatAudit] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}
