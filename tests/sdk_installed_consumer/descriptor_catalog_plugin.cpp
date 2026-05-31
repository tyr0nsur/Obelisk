#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sys/stat.h>

namespace
{
    bool g_DescriptorCatalogValidated = false;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    bool PathExists(const char* path)
    {
        struct stat st {};
        return path && stat(path, &st) == 0;
    }

    bool HasDescriptorApi(const ObeliskApi* api)
    {
        if (!api ||
            api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities))
        {
            return false;
        }

        return api->struct_size >= offsetof(ObeliskApi, DescribeResourceKind) +
                sizeof(api->DescribeResourceKind) &&
            api->struct_size >= offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
                sizeof(api->DescribeGameplayPolicyEventKind) &&
            (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) != 0 &&
            (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) != 0 &&
            api->DescribeResourceKind &&
            api->DescribeGameplayPolicyEventKind;
    }

    bool ValidateResourceKindDescriptor(const ObeliskApi* api,
                                        uint32_t resourceKind,
                                        uint64_t eventMask,
                                        uint64_t fieldMask,
                                        const char* stableName,
                                        const char* displayName)
    {
        ObeliskResourceKindDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        if (!api->DescribeResourceKind(resourceKind, &descriptor))
            return false;

        constexpr uint64_t kRequiredFlags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
        return descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size == sizeof(ObeliskResourceKindDescriptor) &&
            descriptor.resource_kind == resourceKind &&
            descriptor.reserved0 == 0 &&
            (descriptor.flags & kRequiredFlags) == kRequiredFlags &&
            (descriptor.flags & ~kRequiredFlags) == 0 &&
            descriptor.supported_gameplay_policy_event_mask == eventMask &&
            descriptor.supported_gameplay_policy_field_mask == fieldMask &&
            std::strcmp(descriptor.stable_name, stableName) == 0 &&
            std::strcmp(descriptor.display_name, displayName) == 0;
    }

    bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api,
                                               uint32_t eventKind,
                                               uint32_t resourceKind,
                                               uint64_t eventKindMask,
                                               uint64_t fieldMask,
                                               uint64_t backingFlag,
                                               const char* stableName,
                                               const char* displayName)
    {
        ObeliskGameplayPolicyEventDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (!api->DescribeGameplayPolicyEventKind(eventKind, &descriptor))
            return false;

        constexpr uint64_t kKnownBackingFlags =
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
        constexpr uint64_t kKnownFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD | kKnownBackingFlags;
        const uint64_t requiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD | backingFlag;
        return descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor) &&
            descriptor.event_kind == eventKind &&
            descriptor.resource_kind == resourceKind &&
            (descriptor.flags & requiredFlags) == requiredFlags &&
            (descriptor.flags & (kKnownBackingFlags & ~backingFlag)) == 0 &&
            (descriptor.flags & ~kKnownFlags) == 0 &&
            descriptor.event_kind_mask == eventKindMask &&
            descriptor.field_mask == fieldMask &&
            std::strcmp(descriptor.stable_name, stableName) == 0 &&
            std::strcmp(descriptor.display_name, displayName) == 0;
    }

    bool ValidateDescriptorCatalog(const ObeliskApi* api)
    {
        if (!HasDescriptorApi(api))
            return false;

        if (!ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                "structure",
                "Structure"))
        {
            return false;
        }

        if (!ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                "inventory_item",
                "Inventory Item"))
        {
            return false;
        }

        return ValidateGameplayPolicyEventDescriptor(
                   api,
                   OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
                   OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                   OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                   OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                   OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                   "structure.access_check",
                   "Structure Access Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.demolish_check",
                "Structure Demolish Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.variant_change",
                "Structure Variant Change") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.activation_toggle",
                "Structure Activation Toggle") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.pin_code_check",
                "Structure Pin Code Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.seat_check",
                "Structure Seat Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory.remote_add_check",
                "Inventory Remote Add Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory.use_check",
                "Inventory Use Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.allow_equip_check",
                "Inventory Item Allow Equip Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.can_repair_check",
                "Inventory Item Can Repair Check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.use_onto_item_check",
                "Inventory Item Use Onto Item Check");
    }

    bool ValidateRejectedDescriptorQueries(const ObeliskApi* api)
    {
        ObeliskResourceKindDescriptor resourceDescriptor{};
        resourceDescriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        if (api->DescribeResourceKind(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN, &resourceDescriptor))
            return false;

        resourceDescriptor = {};
        resourceDescriptor.struct_size = sizeof(ObeliskResourceKindDescriptor) - 1;
        if (api->DescribeResourceKind(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE, &resourceDescriptor))
            return false;

        ObeliskGameplayPolicyEventDescriptor eventDescriptor{};
        eventDescriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (api->DescribeGameplayPolicyEventKind(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN, &eventDescriptor))
            return false;

        eventDescriptor = {};
        eventDescriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (api->DescribeGameplayPolicyEventKind(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX + 1u, &eventDescriptor))
            return false;

        eventDescriptor = {};
        eventDescriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor) - 1;
        return !api->DescribeGameplayPolicyEventKind(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
            &eventDescriptor);
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
        out->plugin_id = "install_layout_descriptor_catalog_consumer";
        out->name = "Install Layout Descriptor Catalog Consumer";
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

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    try
    {
        g_DescriptorCatalogValidated = false;
        if (!api || !context)
            return false;

        const bool contextOk = context->abi_version == OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION &&
            context->struct_size >= sizeof(ObeliskPluginInitContext) &&
            context->config_dir &&
            context->config_path &&
            context->instance_id &&
            context->plugin_owner_token != 0 &&
            std::strcmp(context->instance_id, "install-layout-test") == 0 &&
            PathExists(context->config_dir) &&
            PathExists(context->config_path);
        if (!contextOk)
            return false;

        g_DescriptorCatalogValidated = ValidateDescriptorCatalog(api) && ValidateRejectedDescriptorQueries(api);
        return g_DescriptorCatalogValidated;
    }
    catch (...)
    {
        g_DescriptorCatalogValidated = false;
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    g_DescriptorCatalogValidated = false;
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_DescriptorCatalogValidated()
{
    return g_DescriptorCatalogValidated;
}
