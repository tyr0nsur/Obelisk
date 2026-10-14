function(obelisk_assert_sdk_target_interface_only target_name)
    if(NOT TARGET ${target_name})
        message(FATAL_ERROR "Missing SDK target: ${target_name}")
    endif()

    get_target_property(sdk_target_type ${target_name} TYPE)
    if(NOT sdk_target_type STREQUAL "INTERFACE_LIBRARY")
        message(FATAL_ERROR "${target_name} must stay interface-only, got: ${sdk_target_type}")
    endif()

    foreach(forbidden_property IN ITEMS
        IMPORTED_IMPLIB
        IMPORTED_LINK_DEPENDENT_LIBRARIES
        IMPORTED_LOCATION
        IMPORTED_OBJECTS
        IMPORTED_SONAME
        INTERFACE_COMPILE_DEFINITIONS
        INTERFACE_COMPILE_OPTIONS
        INTERFACE_LINK_LIBRARIES
        INTERFACE_LINK_OPTIONS
        INTERFACE_SOURCES
        INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
    )
        get_target_property(forbidden_value ${target_name} ${forbidden_property})
        if(forbidden_value AND NOT forbidden_value STREQUAL "forbidden_value-NOTFOUND")
            message(FATAL_ERROR
                "${target_name} must not expose ${forbidden_property}: ${forbidden_value}")
        endif()
    endforeach()
endfunction()

function(obelisk_assert_links_only_sdk target_name)
    get_target_property(link_libraries ${target_name} LINK_LIBRARIES)
    if(NOT link_libraries STREQUAL "obelisk_sdk")
        message(FATAL_ERROR
            "${target_name} must link only obelisk_sdk, got: ${link_libraries}")
    endif()

    foreach(forbidden_link IN ITEMS
        obelisk
        subhook
        dl
        pthread
        Threads::Threads
        "${CMAKE_DL_LIBS}"
    )
        if(forbidden_link AND forbidden_link IN_LIST link_libraries)
            message(FATAL_ERROR
                "${target_name} must not link runtime/private library directly: ${forbidden_link}")
        endif()
    endforeach()
endfunction()

obelisk_assert_sdk_target_interface_only(obelisk_sdk)

add_library(sdk_consumer_minimal_plugin SHARED
    MinimalPlugin.cpp
)
target_link_libraries(sdk_consumer_minimal_plugin PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_minimal_plugin PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
obelisk_assert_links_only_sdk(sdk_consumer_minimal_plugin)

add_library(sdk_consumer_minimal_no_shutdown_plugin SHARED
    MinimalNoShutdownPlugin.cpp
)
target_link_libraries(sdk_consumer_minimal_no_shutdown_plugin PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_minimal_no_shutdown_plugin PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)
obelisk_assert_links_only_sdk(sdk_consumer_minimal_no_shutdown_plugin)

add_library(sdk_consumer_c_abi_plugin SHARED
    CAbiPlugin.c
)
target_link_libraries(sdk_consumer_c_abi_plugin PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_c_abi_plugin PROPERTIES
    PREFIX ""
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
    C_VISIBILITY_PRESET hidden
)
obelisk_assert_links_only_sdk(sdk_consumer_c_abi_plugin)

add_executable(sdk_consumer_abi_layout_guard
    AbiLayoutGuard.c
)
target_link_libraries(sdk_consumer_abi_layout_guard PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_abi_layout_guard PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON
)
obelisk_assert_links_only_sdk(sdk_consumer_abi_layout_guard)

add_executable(sdk_consumer_fixture
    SdkConsumerFixture.cpp
)
target_link_libraries(sdk_consumer_fixture PRIVATE obelisk_sdk dl)
target_include_directories(sdk_consumer_fixture PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../..)

add_test(
    NAME SdkConsumerAbiLayoutGuard
    COMMAND sdk_consumer_abi_layout_guard
)
set_tests_properties(SdkConsumerAbiLayoutGuard PROPERTIES
    LABELS "sdk_consumer;abi_layout;non_claim"
)

add_test(
    NAME SdkConsumerPackageShapeNonClaimGuard
    COMMAND
        ${CMAKE_COMMAND}
        -DOBELISK_BUILD_CMAKE_PACKAGE_DIR=${CMAKE_BINARY_DIR}
        -DOBELISK_PACKAGE_SHAPE_GUARD_WORK_DIR=${CMAKE_CURRENT_BINARY_DIR}/package_shape_non_claim_guard
        -P ${CMAKE_CURRENT_SOURCE_DIR}/PackageShapeNonClaimGuard.cmake
)
set_tests_properties(SdkConsumerPackageShapeNonClaimGuard PROPERTIES
    LABELS "sdk_consumer;package_shape;non_claim"
    RESOURCE_LOCK sdk_consumer_package_shape_non_claim_guard
)

add_test(
    NAME SdkConsumerFixture
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>"
)

add_test(
    NAME SdkConsumerFixtureNoThrowBoundary
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal throw-log-init
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal no-gameplay-policy-capability
)

add_test(
    NAME SdkConsumerFixtureRejectsBadGameplayPolicyDescriptor
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal bad-gameplay-policy-descriptor
)

add_test(
    NAME SdkConsumerFixtureRejectsZeroOwnerToken
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal zero-owner-token
)

add_test(
    NAME SdkConsumerFixtureRejectsShortApiBeforeCapabilities
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-before-capabilities
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-between-gameplay-policy-register-unregister
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-gameplay-policy-register-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-gameplay-policy-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsDescriptorsWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-before-descriptors
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyEventDescriptorsWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-between-descriptor-functions
)

add_test(
    NAME SdkConsumerFixtureSkipsResourceDescriptorsWithNullSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-resource-descriptor-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsGameplayPolicyEventDescriptorsWithNullSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-gameplay-policy-descriptor-slot
)

add_test(
    NAME SdkConsumerFixtureCleansUpFailedGameplayPolicyRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-gameplay-policy-registration
)

add_test(
    NAME SdkConsumerFixtureRejectsZeroGameplayPolicyHandle
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-gameplay-policy-registration
)

add_test(
    NAME SdkConsumerFixtureCleansUpFailedChatMessageRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-chat-message-registration
)

add_test(
    NAME SdkConsumerFixtureRejectsZeroChatMessageHandle
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-chat-message-registration
)

add_test(
    NAME SdkConsumerFixtureCleansUpFailedTimerRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-timer-registration
)

add_test(
    NAME SdkConsumerFixtureRejectsZeroTimerHandle
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal fail-timer-registration
)

add_test(
    NAME SdkConsumerFixtureRejectsResourceDescriptorMissingNoIdentityFlag
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal missing-resource-descriptor-no-identity-flag
)

add_test(
    NAME SdkConsumerFixtureRejectsResourceDescriptorMissingNoLookupFlag
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal missing-resource-descriptor-no-lookup-flag
)

add_test(
    NAME SdkConsumerFixtureCopiesBorrowedInitPointers
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal borrowed-init-pointers
)

add_test(
    NAME SdkConsumerFixtureCopiesBorrowedApiTable
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal borrowed-api-table
)

add_test(
    NAME SdkConsumerFixtureSkipsPostInitCallProcessEvent
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal post-init-call-process-event-skipped
)

add_test(
    NAME SdkConsumerFixtureSkipsChatMessageWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-before-chat-slots
)

add_test(
    NAME SdkConsumerFixtureSkipsChatMessageWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-between-chat-message-register-unregister
)

add_test(
    NAME SdkConsumerFixtureSkipsChatMessageWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-chat-message-register-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsChatMessageWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-chat-message-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsTimerWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-before-timer-slots
)

add_test(
    NAME SdkConsumerFixtureSkipsTimerWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal short-api-between-timer-register-unregister
)

add_test(
    NAME SdkConsumerFixtureSkipsTimerWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-timer-register-slot
)

add_test(
    NAME SdkConsumerFixtureSkipsTimerWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>" sdk_consumer_minimal null-timer-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureNoShutdown
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_no_shutdown_plugin>"
)

add_test(
    NAME SdkConsumerFixtureCAbiPlugin
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginRejectsZeroOwnerToken
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal zero-owner-token
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginRejectsInvalidContext
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal invalid-context
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginRejectsShortApiBeforeCapabilities
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-capabilities
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginShortApiSkipsAppendedCallbacks
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-gameplay-policy
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-between-gameplay-policy-register-unregister
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-gameplay-policy-register-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-gameplay-policy-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsDescriptorsWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-descriptors
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyEventDescriptorsWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-between-descriptor-functions
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsResourceDescriptorsWithNullSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-resource-descriptor-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyEventDescriptorsWithNullSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-gameplay-policy-descriptor-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginRejectsResourceDescriptorMissingNoIdentityFlag
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal missing-resource-descriptor-no-identity-flag
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginRejectsResourceDescriptorMissingNoLookupFlag
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal missing-resource-descriptor-no-lookup-flag
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginCleansUpFailedGameplayPolicyRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal fail-gameplay-policy-registration
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginCleansUpFailedChatMessageRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal fail-chat-message-registration
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginCleansUpFailedTimerRegistration
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal fail-timer-registration
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsChatMessageWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal no-chat-message-capability
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsChatMessageWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-chat-slots
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsChatMessageWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-between-chat-message-register-unregister
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsChatMessageWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-chat-message-register-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsChatMessageWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-chat-message-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal no-timer-capability
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-timer-slots
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithoutUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-between-timer-register-unregister
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithNullRegisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-timer-register-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithNullUnregisterSlot
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal null-timer-unregister-slot
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal no-gameplay-policy-capability
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginCopiesBorrowedInitPointers
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal borrowed-init-pointers
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginCopiesBorrowedApiTable
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal borrowed-api-table
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsPostInitCallProcessEvent
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal post-init-call-process-event-skipped
)

add_test(
    NAME SdkConsumerFixtureOBaseEvents
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsActive
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents active-process-event
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsActiveProcessEventNoFilteredCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents active-process-event-no-filtered-capability
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsActiveProcessEventShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents active-process-event-short-api-before-process-event-handles
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsChatCommandHelper
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents active-chat-command-helper
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsChatCommandHelperNoCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents active-chat-command-helper-no-chat-capability
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsChatPostRegistrationFailureCleanup
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents throw-log-after-chat-message-registration
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsCallbackNoThrow
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents callback-throw-log
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsNoThrowBoundary
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents throw-log-init
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsRejectsMapAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents unsupported-map-allowlist
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsRejectsInvalidContext
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents invalid-context
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsRejectsInvalidProcessEventConfig
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents invalid-process-event-config
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsRejectsInvalidChatCommandConfig
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents invalid-chat-command-config
)

add_test(
    NAME SdkConsumerFixtureOBaseEventsRejectsUnsafeInstanceAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents unsafe-instance-allowlist
)

add_test(
    NAME SdkConsumerFixtureOProcessTimer
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerActive
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer active-timer
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerDoubleShutdown
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer active-timer-double-shutdown
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerNoTimerCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer no-timer-capability
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer short-api-before-gameplay-policy
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerActiveNoTimerCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer active-timer-no-timer-capability
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerActiveShortApiBeforeTimerSlots
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer active-timer-short-api-before-timer-slots
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerRejectsZeroOwnerToken
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer zero-owner-token
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerRegistrationFailure
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer fail-timer-registration
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerCleansUpPostRegistrationInitFailure
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer throw-log-after-timer-registration
)

add_test(
    NAME SdkConsumerFixtureOProcessTimerRejectsUnsafeInstanceAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oProcessTimer>" oProcessTimer unsafe-instance-allowlist
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalog
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogActive
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog active-descriptor-catalog
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogDisabledNoDescriptorCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog disabled-no-descriptor-capability
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogNoDescriptorCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog no-descriptor-capability
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogShortApi
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog short-api-before-descriptors
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogBadMetadata
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog bad-descriptor-catalog-metadata
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogBadName
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog bad-descriptor-catalog-name
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogBadFlags
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog bad-descriptor-catalog-flags
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogInvalidConfig
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog invalid-descriptor-catalog-config
)

add_test(
    NAME SdkConsumerFixtureODescriptorCatalogRejectsUnsafeInstanceAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oDescriptorCatalog>" oDescriptorCatalog unsafe-instance-allowlist
)

if(TARGET oPolicyAudit)
    add_test(
        NAME SdkConsumerFixtureOPolicyAudit
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oPolicyAudit>" oPolicyAudit
    )

    add_test(
        NAME SdkConsumerFixtureOPolicyAuditActiveNoGameplayPolicyCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oPolicyAudit>" oPolicyAudit active-policy-audit-no-gameplay-policy-capability
    )

    add_test(
        NAME SdkConsumerFixtureOPolicyAuditActiveShortApi
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oPolicyAudit>" oPolicyAudit active-policy-audit-short-api-before-gameplay-policy
    )

    add_test(
        NAME SdkConsumerFixtureOPolicyAuditPostRegistrationFailureCleanup
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oPolicyAudit>" oPolicyAudit throw-log-after-gameplay-policy-registration
    )
endif()

if(TARGET oChatLogger)
    add_test(
        NAME SdkConsumerFixtureOChatLogger
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatLogger>" oChatLogger
    )

    add_test(
        NAME SdkConsumerFixtureOChatLoggerActive
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatLogger>" oChatLogger active-chat-logger
    )

    add_test(
        NAME SdkConsumerFixtureOChatLoggerNoChatCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatLogger>" oChatLogger active-chat-logger-no-chat-capability
    )

    add_test(
        NAME SdkConsumerFixtureOChatLoggerActiveShortApi
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatLogger>" oChatLogger active-chat-logger-short-api-before-chat-slots
    )
endif()

if(TARGET oChatAudit)
    add_test(
        NAME SdkConsumerFixtureOChatAudit
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditActive
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit active-chat-audit
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditDoubleShutdown
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit active-chat-audit-double-shutdown
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditNoChatCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit no-chat-message-capability
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditNoTimerCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit no-timer-capability
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditActiveShortApiBeforeChatSlots
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit active-chat-audit-short-api-before-chat-slots
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditActiveShortApiBeforeTimerSlots
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit active-chat-audit-short-api-before-timer-slots
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditDisabledNoChatCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit disabled-no-chat-message-capability
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditDisabledNoTimerCapability
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit disabled-no-timer-capability
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditDisabledShortApi
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit disabled-short-api-before-chat-slots
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditRejectsZeroOwnerToken
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit zero-owner-token
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditRejectsInvalidConfig
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit invalid-chat-audit-config
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditChatRegistrationFailure
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit fail-chat-message-registration
    )

    add_test(
        NAME SdkConsumerFixtureOChatAuditTimerRegistrationFailure
        COMMAND sdk_consumer_fixture "$<TARGET_FILE:oChatAudit>" oChatAudit fail-timer-registration
    )
endif()
