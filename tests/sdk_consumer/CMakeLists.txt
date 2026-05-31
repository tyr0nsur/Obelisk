add_library(sdk_consumer_minimal_plugin SHARED
    MinimalPlugin.cpp
)
target_link_libraries(sdk_consumer_minimal_plugin PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_minimal_plugin PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_library(sdk_consumer_minimal_no_shutdown_plugin SHARED
    MinimalNoShutdownPlugin.cpp
)
target_link_libraries(sdk_consumer_minimal_no_shutdown_plugin PRIVATE obelisk_sdk)
set_target_properties(sdk_consumer_minimal_no_shutdown_plugin PROPERTIES
    PREFIX ""
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

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

add_executable(sdk_consumer_fixture
    SdkConsumerFixture.cpp
)
target_link_libraries(sdk_consumer_fixture PRIVATE obelisk_sdk dl)

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
    NAME SdkConsumerFixtureNoShutdown
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_no_shutdown_plugin>"
)

add_test(
    NAME SdkConsumerFixtureCAbiPlugin
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginShortApiSkipsAppendedCallbacks
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal short-api-before-gameplay-policy
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
    NAME SdkConsumerFixtureCAbiPluginSkipsTimerWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal no-timer-capability
)

add_test(
    NAME SdkConsumerFixtureCAbiPluginSkipsGameplayPolicyWithoutCapability
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal no-gameplay-policy-capability
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
