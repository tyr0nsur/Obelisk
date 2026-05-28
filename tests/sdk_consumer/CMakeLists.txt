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
    NAME SdkConsumerFixtureNoShutdown
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_no_shutdown_plugin>"
)

add_test(
    NAME SdkConsumerFixtureCAbiPlugin
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_c_abi_plugin>" c_abi_minimal
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
    NAME SdkConsumerFixtureOBaseEventsRejectsUnsafeInstanceAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents unsafe-instance-allowlist
)
