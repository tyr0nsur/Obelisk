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

add_executable(sdk_consumer_fixture
    SdkConsumerFixture.cpp
)
target_link_libraries(sdk_consumer_fixture PRIVATE obelisk_sdk dl)

add_test(
    NAME SdkConsumerFixture
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_plugin>"
)

add_test(
    NAME SdkConsumerFixtureNoShutdown
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:sdk_consumer_minimal_no_shutdown_plugin>"
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
    NAME SdkConsumerFixtureOBaseEventsRejectsMapAllowlist
    COMMAND sdk_consumer_fixture "$<TARGET_FILE:oBaseEvents>" oBaseEvents unsupported-map-allowlist
)
