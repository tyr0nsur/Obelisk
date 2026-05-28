#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <type_traits>

#ifdef OBELISK_API_CAPABILITY_CHAT_EVENTS
#error "Public chat API must stay gated until chat ABI promotion requirements are complete."
#endif

namespace
{
    template <typename T>
    constexpr void AssertAbiType()
    {
        static_assert(std::is_standard_layout_v<T>);
        static_assert(std::is_trivial_v<T>);
        static_assert(std::is_trivially_copyable_v<T>);
    }

    void RuntimeNoOp()
    {
        volatile std::uint32_t apiVersion = OBELISK_API_ABI_VERSION;
        volatile std::uint32_t metadataVersion = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        volatile std::uint32_t initContextVersion = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        volatile std::uint64_t ownedCallbacksCapability = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;
        volatile std::uint64_t globalCallbacksCapability = OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS;

        (void)apiVersion;
        (void)metadataVersion;
        (void)initContextVersion;
        (void)ownedCallbacksCapability;
        (void)globalCallbacksCapability;
    }
}

int main()
{
    static_assert(sizeof(void*) == 8, "Obelisk ABI layout tests target Linux x86_64");

    AssertAbiType<ObeliskPluginMetadata>();
    static_assert(alignof(ObeliskPluginMetadata) == 8);
    static_assert(sizeof(ObeliskPluginMetadata) == 48);
    static_assert(offsetof(ObeliskPluginMetadata, abi_version) == 0);
    static_assert(offsetof(ObeliskPluginMetadata, struct_size) == 4);
    static_assert(offsetof(ObeliskPluginMetadata, plugin_id) == 8);
    static_assert(offsetof(ObeliskPluginMetadata, name) == 16);
    static_assert(offsetof(ObeliskPluginMetadata, version) == 24);
    static_assert(offsetof(ObeliskPluginMetadata, config_file) == 32);
    static_assert(offsetof(ObeliskPluginMetadata, default_config_json) == 40);

    AssertAbiType<ObeliskPluginInitContext>();
    static_assert(alignof(ObeliskPluginInitContext) == 8);
    static_assert(sizeof(ObeliskPluginInitContext) == 32);
    static_assert(offsetof(ObeliskPluginInitContext, abi_version) == 0);
    static_assert(offsetof(ObeliskPluginInitContext, struct_size) == 4);
    static_assert(offsetof(ObeliskPluginInitContext, config_dir) == 8);
    static_assert(offsetof(ObeliskPluginInitContext, config_path) == 16);
    static_assert(offsetof(ObeliskPluginInitContext, instance_id) == 24);

    AssertAbiType<ObeliskApi>();
    static_assert(alignof(ObeliskApi) == 8);
    static_assert(sizeof(ObeliskApi) == 80);
    static_assert(offsetof(ObeliskApi, LogInfo) == 0);
    static_assert(offsetof(ObeliskApi, LogWarn) == 8);
    static_assert(offsetof(ObeliskApi, LogError) == 16);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEvent) == 24);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEvent) == 32);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndex) == 40);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndex) == 48);
    static_assert(offsetof(ObeliskApi, CallProcessEvent) == 56);
    static_assert(offsetof(ObeliskApi, abi_version) == 64);
    static_assert(offsetof(ObeliskApi, struct_size) == 68);
    static_assert(offsetof(ObeliskApi, capabilities) == 72);

    static_assert(offsetof(ObeliskApi, abi_version) > offsetof(ObeliskApi, CallProcessEvent));
    static_assert(offsetof(ObeliskApi, struct_size) > offsetof(ObeliskApi, abi_version));
    static_assert(offsetof(ObeliskApi, capabilities) > offsetof(ObeliskApi, struct_size));
    static_assert(offsetof(ObeliskApi, capabilities) + sizeof(ObeliskApi::capabilities) == sizeof(ObeliskApi));

    RuntimeNoOp();
    return 0;
}
