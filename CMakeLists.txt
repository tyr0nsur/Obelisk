cmake_minimum_required(VERSION 3.22)
project(Obelisk VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
find_package(OpenSSL REQUIRED COMPONENTS Crypto)

set(OBELISK_DEVELOPMENT_LINE "0.1.0-dev")
set(OBELISK_RELEASE_CHANNEL "dev")
set(OBELISK_PUBLIC_API_HEADER "${CMAKE_CURRENT_SOURCE_DIR}/include/obelisk/ObeliskApi.h")

function(obelisk_read_public_abi_version macro_name)
    file(STRINGS "${OBELISK_PUBLIC_API_HEADER}" abi_version_lines
        REGEX "^[ \t]*#define[ \t]+${macro_name}[ \t]+[0-9]+u[ \t]*$")
    list(LENGTH abi_version_lines abi_version_count)
    if(NOT abi_version_count EQUAL 1)
        message(FATAL_ERROR
            "Expected exactly one public ABI version macro ${macro_name} in ${OBELISK_PUBLIC_API_HEADER}")
    endif()

    string(REGEX REPLACE
        "^[ \t]*#define[ \t]+${macro_name}[ \t]+([0-9]+)u[ \t]*$"
        "\\1"
        abi_version
        "${abi_version_lines}")
    set(${macro_name} "${abi_version}" PARENT_SCOPE)
endfunction()

obelisk_read_public_abi_version(OBELISK_API_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_PLUGIN_METADATA_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION)
obelisk_read_public_abi_version(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION)

# Use fPIC as it's a shared library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

enable_testing()
set(SUBHOOK_NO_TESTS ON CACHE BOOL "Disable subhook tests" FORCE)
option(OBELISK_BUILD_EXPERIMENTAL_PLUGINS "Build experimental first-party plugins outside the release scope" OFF)

add_library(obelisk_sdk INTERFACE)
target_include_directories(obelisk_sdk INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

function(obelisk_assert_sdk_interface_only target_name)
    if(NOT TARGET ${target_name})
        message(FATAL_ERROR "Missing SDK target: ${target_name}")
    endif()

    get_target_property(sdk_target_type ${target_name} TYPE)
    if(NOT sdk_target_type STREQUAL "INTERFACE_LIBRARY")
        message(FATAL_ERROR "${target_name} must stay an interface-only SDK target, got: ${sdk_target_type}")
    endif()

    foreach(forbidden_property IN ITEMS
        IMPORTED_IMPLIB
        IMPORTED_IMPLIB_DEBUG
        IMPORTED_IMPLIB_MINSIZEREL
        IMPORTED_IMPLIB_RELEASE
        IMPORTED_IMPLIB_RELWITHDEBINFO
        IMPORTED_LINK_DEPENDENT_LIBRARIES
        IMPORTED_LINK_DEPENDENT_LIBRARIES_DEBUG
        IMPORTED_LINK_DEPENDENT_LIBRARIES_MINSIZEREL
        IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE
        IMPORTED_LINK_DEPENDENT_LIBRARIES_RELWITHDEBINFO
        IMPORTED_LOCATION
        IMPORTED_LOCATION_DEBUG
        IMPORTED_LOCATION_MINSIZEREL
        IMPORTED_LOCATION_RELEASE
        IMPORTED_LOCATION_RELWITHDEBINFO
        IMPORTED_OBJECTS
        IMPORTED_OBJECTS_DEBUG
        IMPORTED_OBJECTS_MINSIZEREL
        IMPORTED_OBJECTS_RELEASE
        IMPORTED_OBJECTS_RELWITHDEBINFO
        IMPORTED_SONAME
        IMPORTED_SONAME_DEBUG
        IMPORTED_SONAME_MINSIZEREL
        IMPORTED_SONAME_RELEASE
        IMPORTED_SONAME_RELWITHDEBINFO
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

obelisk_assert_sdk_interface_only(obelisk_sdk)

# Dependencies
include(FetchContent)

# fmt library
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        f5e54359df4c26b6230fc61d38aa294581393084
)
FetchContent_MakeAvailable(fmt)

# spdlog library
FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        7e635fca68d014934b4af8a1cf874f63989352b7
)
FetchContent_MakeAvailable(spdlog)

# subhook library
FetchContent_Declare(
    subhook
    GIT_REPOSITORY https://github.com/wyrover/subhook.git
    GIT_TAG        568d2e5a5d6013907e8008857968906b33ef3b7d
)
FetchContent_MakeAvailable(subhook)

# Create the Obelisk shared library
add_library(obelisk SHARED
    loader/Bootstrap.cpp
    runtime/Logger.cpp
    runtime/RuntimeMarkers.cpp
    runtime/BinaryIdentity.cpp
    ue/Memory.cpp
    ue/SafeMemoryRead.cpp
    ue/NativeChatText.cpp
    ue/ObjectClassValidation.cpp
    ue/BuffReflection.cpp
    ue/ChatReflection.cpp
    ue/DinoReflection.cpp
    ue/ItemReflection.cpp
    ue/InventoryReflection.cpp
    ue/StructureReflection.cpp
    ue/PlayerPrincipalLifecycleReflection.cpp
    ue/RuntimeReflection.cpp
    ue/ReflectionScanner.cpp
    hooks/HookManager.cpp
    hooks/StartupNativeHook.cpp
    hooks/NativeChatHook.cpp
    hooks/ProcessEventCallGuard.cpp
    hooks/ProcessEventDispatch.cpp
    hooks/ProcessEventBuffReflection.cpp
    hooks/ProcessEventChatReflection.cpp
    hooks/ProcessEventDinoReflection.cpp
    hooks/ProcessEventInventoryReflection.cpp
    hooks/ProcessEventItemReflection.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp
    hooks/ProcessEventStructureReflection.cpp
    hooks/ProcessEventHook.cpp
    core/ChatEventDispatcher.cpp
    core/CommandDispatcher.cpp
    core/PlayerLifecycleDispatcher.cpp
    core/InventoryPolicyEventDispatcher.cpp
    core/ItemReturnEventDispatcher.cpp
    core/PlayerPrincipalEventDispatcher.cpp
    core/PlayerPrincipalRegistry.cpp
    core/StructureAggregateCensus.cpp
    core/StructureEventDispatcher.cpp
    core/TimerManager.cpp
    core/EventManager.cpp
    core/PluginConfig.cpp
    core/PluginManager.cpp
)

# Includes and linking
target_include_directories(obelisk PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(obelisk PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog subhook dl pthread stdc++fs OpenSSL::Crypto)

# Ensure visibility is hidden by default, and we only export what we want
# (Good practice for LD_PRELOAD plugins)
set_target_properties(obelisk PROPERTIES CXX_VISIBILITY_PRESET hidden)
set_target_properties(obelisk PROPERTIES VISIBILITY_INLINES_HIDDEN 1)
set_target_properties(obelisk PROPERTIES BUILD_RPATH "\$ORIGIN")
set_target_properties(obelisk PROPERTIES INSTALL_RPATH "\$ORIGIN")

add_subdirectory(plugins/oBaseEvents)
add_subdirectory(plugins/oPing)
add_subdirectory(plugins/oProcessTimer)
add_subdirectory(plugins/oDescriptorCatalog)
if(OBELISK_BUILD_EXPERIMENTAL_PLUGINS)
    add_subdirectory(plugins/oPolicyAudit)
    add_subdirectory(plugins/oChatLogger)
    add_subdirectory(plugins/oChatAudit)
endif()
add_subdirectory(tests/sdk_consumer)

add_executable(plugin_config_tests
    tests/core/PluginConfigTests.cpp
    core/PluginConfig.cpp
)
target_include_directories(plugin_config_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(plugin_config_tests PRIVATE obelisk_sdk stdc++fs)

add_test(NAME PluginConfigTests COMMAND plugin_config_tests)

add_executable(event_manager_tests
    tests/core/EventManagerTests.cpp
    core/EventManager.cpp
    runtime/Logger.cpp
    runtime/RuntimeMarkers.cpp
)
target_include_directories(event_manager_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(event_manager_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog)

add_test(NAME EventManagerTests COMMAND event_manager_tests)

add_executable(process_event_dispatch_tests
    tests/core/ProcessEventDispatchTests.cpp
    hooks/ProcessEventCallGuard.cpp
    hooks/ProcessEventDispatch.cpp
    core/EventManager.cpp
    runtime/Logger.cpp
    runtime/RuntimeMarkers.cpp
)
target_include_directories(process_event_dispatch_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(process_event_dispatch_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog)

add_test(NAME ProcessEventDispatchTests COMMAND process_event_dispatch_tests)

add_executable(logger_tests
    tests/runtime/LoggerTests.cpp
    runtime/Logger.cpp
)
target_include_directories(logger_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(logger_tests PRIVATE fmt::fmt spdlog::spdlog stdc++fs)

add_test(NAME LoggerTests COMMAND logger_tests)

add_executable(chat_event_dispatcher_tests
    tests/core/ChatEventDispatcherTests.cpp
    core/ChatEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(chat_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(chat_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME ChatEventDispatcherTests COMMAND chat_event_dispatcher_tests)

add_executable(structure_event_dispatcher_tests
    tests/core/StructureEventDispatcherTests.cpp
    core/StructureEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(structure_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(structure_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME StructureEventDispatcherTests COMMAND structure_event_dispatcher_tests)

add_executable(structure_aggregate_census_tests
    tests/core/StructureAggregateCensusTests.cpp
    core/StructureAggregateCensus.cpp
)
target_include_directories(structure_aggregate_census_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME StructureAggregateCensusTests COMMAND structure_aggregate_census_tests)

add_executable(inventory_policy_event_dispatcher_tests
    tests/core/InventoryPolicyEventDispatcherTests.cpp
    core/InventoryPolicyEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(inventory_policy_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(inventory_policy_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME InventoryPolicyEventDispatcherTests COMMAND inventory_policy_event_dispatcher_tests)

add_executable(item_return_event_dispatcher_tests
    tests/core/ItemReturnEventDispatcherTests.cpp
    core/ItemReturnEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(item_return_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(item_return_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME ItemReturnEventDispatcherTests COMMAND item_return_event_dispatcher_tests)

add_executable(mission_copied_bool_event_dispatcher_tests
    tests/core/MissionCopiedBoolEventDispatcherTests.cpp
    core/MissionCopiedBoolEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(mission_copied_bool_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(mission_copied_bool_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME MissionCopiedBoolEventDispatcherTests COMMAND mission_copied_bool_event_dispatcher_tests)

add_executable(player_principal_event_dispatcher_tests
    tests/core/PlayerPrincipalEventDispatcherTests.cpp
    core/PlayerPrincipalEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(player_principal_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(player_principal_event_dispatcher_tests
    PRIVATE OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS=1
)
target_link_libraries(player_principal_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME PlayerPrincipalEventDispatcherTests COMMAND player_principal_event_dispatcher_tests)

add_executable(player_principal_registry_tests
    tests/core/PlayerPrincipalRegistryTests.cpp
    core/PlayerPrincipalRegistry.cpp
)
target_include_directories(player_principal_registry_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(player_principal_registry_tests
    PRIVATE OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS=1
)

add_test(NAME PlayerPrincipalRegistryTests COMMAND player_principal_registry_tests)

add_executable(plugin_manager_tests
    tests/core/PluginManagerTests.cpp
    tests/core/PingPluginIntegrationTests.cpp
    core/ChatEventDispatcher.cpp
    core/CommandDispatcher.cpp
    core/PlayerLifecycleDispatcher.cpp
    core/InventoryPolicyEventDispatcher.cpp
    core/ItemReturnEventDispatcher.cpp
    core/PlayerPrincipalEventDispatcher.cpp
    core/StructureEventDispatcher.cpp
    core/TimerManager.cpp
    core/EventManager.cpp
    core/PluginConfig.cpp
    core/PluginManager.cpp
    runtime/Logger.cpp
    runtime/RuntimeMarkers.cpp
    tests/core/ProcessEventHookStub.cpp
)
target_include_directories(plugin_manager_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(plugin_manager_tests
    PRIVATE OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS=1
    OBELISK_PING_PLUGIN_PATH="$<TARGET_FILE:oPing>"
)
add_dependencies(plugin_manager_tests oPing)
target_link_libraries(plugin_manager_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog dl stdc++fs)

add_test(NAME PluginManagerTests COMMAND plugin_manager_tests)

add_executable(command_dispatcher_tests
    tests/core/CommandDispatcherTests.cpp
    core/CommandDispatcher.cpp
)
target_include_directories(command_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(command_dispatcher_tests PRIVATE obelisk_sdk pthread)
add_test(NAME CommandDispatcherTests COMMAND command_dispatcher_tests)

add_executable(player_lifecycle_dispatcher_tests
    tests/core/PlayerLifecycleDispatcherTests.cpp
    core/PlayerLifecycleDispatcher.cpp
)
target_include_directories(player_lifecycle_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(player_lifecycle_dispatcher_tests PRIVATE obelisk_sdk pthread)
add_test(NAME PlayerLifecycleDispatcherTests COMMAND player_lifecycle_dispatcher_tests)

add_executable(startup_native_hook_tests
    tests/core/StartupNativeHookTests.cpp
    hooks/StartupNativeHook.cpp
    ue/SafeMemoryRead.cpp
)
target_include_directories(startup_native_hook_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(startup_native_hook_tests PRIVATE pthread)
add_test(NAME StartupNativeHookTests COMMAND startup_native_hook_tests)

add_executable(safe_memory_read_tests tests/core/SafeMemoryReadTests.cpp ue/SafeMemoryRead.cpp)
target_include_directories(safe_memory_read_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
add_test(NAME SafeMemoryReadTests COMMAND safe_memory_read_tests)

add_executable(object_class_validation_tests
    tests/core/ObjectClassValidationTests.cpp
    ue/ObjectClassValidation.cpp
    ue/SafeMemoryRead.cpp
)
target_include_directories(object_class_validation_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
add_test(NAME ObjectClassValidationTests COMMAND object_class_validation_tests)

add_executable(native_chat_text_tests tests/core/NativeChatTextTests.cpp ue/NativeChatText.cpp ue/SafeMemoryRead.cpp)
target_include_directories(native_chat_text_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
add_test(NAME NativeChatTextTests COMMAND native_chat_text_tests)

add_executable(native_player_lifecycle_frame_tests
    tests/core/NativePlayerLifecycleFrameTests.cpp
    hooks/NativeChatHook.cpp
    hooks/StartupNativeHook.cpp
    core/CommandDispatcher.cpp
    core/PlayerLifecycleDispatcher.cpp
    runtime/BinaryIdentity.cpp
    runtime/Logger.cpp
    ue/Memory.cpp
    ue/SafeMemoryRead.cpp
    ue/NativeChatText.cpp
    ue/ObjectClassValidation.cpp
)
target_include_directories(native_player_lifecycle_frame_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(native_player_lifecycle_frame_tests PRIVATE
    obelisk_sdk fmt::fmt spdlog::spdlog OpenSSL::Crypto dl pthread)
add_test(NAME NativePlayerLifecycleFrameTests COMMAND native_player_lifecycle_frame_tests)

add_executable(binary_identity_tests tests/core/BinaryIdentityTests.cpp runtime/BinaryIdentity.cpp)
target_include_directories(binary_identity_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(binary_identity_tests PRIVATE OpenSSL::Crypto)
add_test(NAME BinaryIdentityTests COMMAND binary_identity_tests)

add_executable(timer_manager_tests
    tests/core/TimerManagerTests.cpp
    core/TimerManager.cpp
    runtime/Logger.cpp
)
target_include_directories(timer_manager_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(timer_manager_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME TimerManagerTests COMMAND timer_manager_tests)

add_executable(abi_layout_tests
    tests/abi/AbiLayoutTests.cpp
)
target_link_libraries(abi_layout_tests PRIVATE obelisk_sdk)

add_test(NAME AbiLayoutTests COMMAND abi_layout_tests)

add_executable(c_abi_layout_tests
    tests/abi/CAbiLayoutTests.c
)
target_link_libraries(c_abi_layout_tests PRIVATE obelisk_sdk)

add_test(NAME CAbiLayoutTests COMMAND c_abi_layout_tests)

add_executable(runtime_reflection_tests
    tests/core/RuntimeReflectionTests.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(runtime_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME RuntimeReflectionTests COMMAND runtime_reflection_tests)

add_executable(memory_tests
    tests/core/MemoryTests.cpp
    ue/Memory.cpp
    runtime/Logger.cpp
)
target_include_directories(memory_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(memory_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME MemoryTests COMMAND memory_tests)

add_executable(runtime_marker_tests
    tests/core/RuntimeMarkerTests.cpp
    runtime/RuntimeMarkers.cpp
)
target_include_directories(runtime_marker_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME RuntimeMarkerTests COMMAND runtime_marker_tests)

add_executable(process_event_call_guard_tests
    tests/core/ProcessEventCallGuardTests.cpp
    hooks/ProcessEventCallGuard.cpp
)
target_include_directories(process_event_call_guard_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventCallGuardTests COMMAND process_event_call_guard_tests)

add_executable(permissions_admin_decision_model_tests
    tests/core/PermissionsAdminDecisionModelTests.cpp
    core/AuthzDecisionModel.cpp
)
target_include_directories(permissions_admin_decision_model_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME PermissionsAdminDecisionModelTests COMMAND permissions_admin_decision_model_tests)

add_executable(chat_reflection_tests
    tests/core/ChatReflectionTests.cpp
    ue/ChatReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(chat_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ChatReflectionTests COMMAND chat_reflection_tests)

add_executable(buff_reflection_tests
    tests/core/BuffReflectionTests.cpp
    ue/BuffReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(buff_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME BuffReflectionTests COMMAND buff_reflection_tests)

add_executable(dino_reflection_tests
    tests/core/DinoReflectionTests.cpp
    hooks/ProcessEventDinoReflection.cpp
    ue/DinoReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(dino_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME DinoReflectionTests COMMAND dino_reflection_tests)

add_executable(process_event_dino_reflection_tests
    tests/core/ProcessEventDinoReflectionTests.cpp
    hooks/ProcessEventDinoReflection.cpp
    ue/DinoReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_dino_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventDinoReflectionTests COMMAND process_event_dino_reflection_tests)

add_executable(mission_reflection_tests
    tests/core/MissionReflectionTests.cpp
    ue/MissionReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(mission_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME MissionReflectionTests COMMAND mission_reflection_tests)

add_executable(process_event_mission_reflection_tests
    tests/core/ProcessEventMissionReflectionTests.cpp
    hooks/ProcessEventMissionReflection.cpp
    core/MissionCopiedBoolEventDispatcher.cpp
    ue/MissionReflection.cpp
    ue/RuntimeReflection.cpp
    runtime/Logger.cpp
)
target_include_directories(process_event_mission_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(process_event_mission_reflection_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME ProcessEventMissionReflectionTests COMMAND process_event_mission_reflection_tests)

add_executable(transfer_reflection_tests
    tests/core/TransferReflectionTests.cpp
    ue/TransferReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(transfer_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME TransferReflectionTests COMMAND transfer_reflection_tests)

add_executable(process_event_transfer_reflection_tests
    tests/core/ProcessEventTransferReflectionTests.cpp
    hooks/ProcessEventTransferReflection.cpp
    ue/TransferReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_transfer_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventTransferReflectionTests COMMAND process_event_transfer_reflection_tests)

add_executable(structure_reflection_tests
    tests/core/StructureReflectionTests.cpp
    ue/StructureReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(structure_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME StructureReflectionTests COMMAND structure_reflection_tests)

add_executable(inventory_reflection_tests
    tests/core/InventoryReflectionTests.cpp
    ue/InventoryReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(inventory_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME InventoryReflectionTests COMMAND inventory_reflection_tests)

add_executable(item_reflection_tests
    tests/core/ItemReflectionTests.cpp
    ue/ItemReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(item_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ItemReflectionTests COMMAND item_reflection_tests)

add_executable(player_principal_lifecycle_reflection_tests
    tests/core/PlayerPrincipalLifecycleReflectionTests.cpp
    ue/PlayerPrincipalLifecycleReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(player_principal_lifecycle_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME PlayerPrincipalLifecycleReflectionTests COMMAND player_principal_lifecycle_reflection_tests)

add_executable(player_principal_lifecycle_applicator_tests
    tests/core/PlayerPrincipalLifecycleApplicatorTests.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp
    core/PlayerPrincipalEventDispatcher.cpp
    core/PlayerPrincipalRegistry.cpp
    runtime/Logger.cpp
    ue/PlayerPrincipalLifecycleReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(player_principal_lifecycle_applicator_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_definitions(player_principal_lifecycle_applicator_tests
    PRIVATE
        OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS=1
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS=1
)
target_link_libraries(player_principal_lifecycle_applicator_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME PlayerPrincipalLifecycleApplicatorTests COMMAND player_principal_lifecycle_applicator_tests)

add_executable(process_event_player_principal_lifecycle_observer_tests
    tests/core/ProcessEventPlayerPrincipalLifecycleObserverTests.cpp
    hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp
    ue/PlayerPrincipalLifecycleReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_player_principal_lifecycle_observer_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventPlayerPrincipalLifecycleObserverTests COMMAND process_event_player_principal_lifecycle_observer_tests)

add_executable(process_event_item_reflection_tests
    tests/core/ProcessEventItemReflectionTests.cpp
    hooks/ProcessEventItemReflection.cpp
    ue/ItemReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_item_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventItemReflectionTests COMMAND process_event_item_reflection_tests)

add_executable(process_event_buff_reflection_tests
    tests/core/ProcessEventBuffReflectionTests.cpp
    hooks/ProcessEventBuffReflection.cpp
    ue/BuffReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_buff_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventBuffReflectionTests COMMAND process_event_buff_reflection_tests)

add_executable(process_event_chat_reflection_tests
    tests/core/ProcessEventChatReflectionTests.cpp
    hooks/ProcessEventChatReflection.cpp
    ue/ChatReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_chat_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventChatReflectionTests COMMAND process_event_chat_reflection_tests)

add_executable(process_event_inventory_reflection_tests
    tests/core/ProcessEventInventoryReflectionTests.cpp
    hooks/ProcessEventInventoryReflection.cpp
    core/InventoryPolicyEventDispatcher.cpp
    ue/InventoryReflection.cpp
    ue/RuntimeReflection.cpp
    runtime/Logger.cpp
)
target_include_directories(process_event_inventory_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(process_event_inventory_reflection_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME ProcessEventInventoryReflectionTests COMMAND process_event_inventory_reflection_tests)

add_executable(process_event_structure_reflection_tests
    tests/core/ProcessEventStructureReflectionTests.cpp
    hooks/ProcessEventCallGuard.cpp
    hooks/ProcessEventDispatch.cpp
    hooks/ProcessEventStructureReflection.cpp
    core/EventManager.cpp
    core/StructureEventDispatcher.cpp
    ue/StructureReflection.cpp
    ue/RuntimeReflection.cpp
    runtime/Logger.cpp
    runtime/RuntimeMarkers.cpp
)
target_include_directories(process_event_structure_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(process_event_structure_reflection_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog)

add_test(NAME ProcessEventStructureReflectionTests COMMAND process_event_structure_reflection_tests)

add_executable(chat_reflection_benchmark EXCLUDE_FROM_ALL
    tests/perf/ChatReflectionBenchmark.cpp
    hooks/ProcessEventChatReflection.cpp
    ue/ChatReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(chat_reflection_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(item_return_event_dispatcher_benchmark EXCLUDE_FROM_ALL
    tests/perf/ItemReturnEventDispatcherBenchmark.cpp
    core/ItemReturnEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(item_return_event_dispatcher_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(item_return_event_dispatcher_benchmark PRIVATE fmt::fmt spdlog::spdlog)

add_executable(structure_event_dispatcher_benchmark EXCLUDE_FROM_ALL
    tests/perf/StructureEventDispatcherBenchmark.cpp
    core/StructureEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(structure_event_dispatcher_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(structure_event_dispatcher_benchmark PRIVATE fmt::fmt spdlog::spdlog)

add_executable(inventory_policy_event_dispatcher_benchmark EXCLUDE_FROM_ALL
    tests/perf/InventoryPolicyEventDispatcherBenchmark.cpp
    core/InventoryPolicyEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(inventory_policy_event_dispatcher_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(inventory_policy_event_dispatcher_benchmark PRIVATE fmt::fmt spdlog::spdlog)

add_executable(mission_copied_bool_event_dispatcher_benchmark EXCLUDE_FROM_ALL
    tests/perf/MissionCopiedBoolEventDispatcherBenchmark.cpp
    core/MissionCopiedBoolEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(mission_copied_bool_event_dispatcher_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(mission_copied_bool_event_dispatcher_benchmark PRIVATE fmt::fmt spdlog::spdlog)

install(TARGETS obelisk
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    COMPONENT Runtime
)

install(TARGETS obelisk_sdk
    EXPORT ObeliskTargets
    COMPONENT SDK
)

install(FILES include/obelisk/ObeliskApi.h include/obelisk/ObeliskCommandApi.h
    include/obelisk/ObeliskPlayerLifecycleApi.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/obelisk
    COMPONENT SDK
)

install(EXPORT ObeliskTargets
    NAMESPACE Obelisk::
    FILE ObeliskTargets.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Obelisk
    COMPONENT SDK
)

configure_package_config_file(
    cmake/ObeliskConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Obelisk
)

set(OBELISK_CONFIG_GUARDRAILS_CONTENT [=[
if(NOT Obelisk_FIND_VERSION)
    set(Obelisk_FOUND FALSE)
    set(Obelisk_NOT_FOUND_MESSAGE
        "Obelisk SDK package-shape requires an explicit non-EXACT version request with COMPONENTS SDK.")
    return()
endif()

if(Obelisk_FIND_VERSION_EXACT)
    set(Obelisk_FOUND FALSE)
    set(Obelisk_NOT_FOUND_MESSAGE
        "Obelisk SDK package-shape does not satisfy EXACT stable-version requests.")
    return()
endif()

if(NOT Obelisk_FIND_COMPONENTS)
    set(Obelisk_FOUND FALSE)
    set(Obelisk_NOT_FOUND_MESSAGE
        "Obelisk SDK package-shape requires find_package(... COMPONENTS SDK).")
    return()
endif()

foreach(_obelisk_requested_component IN LISTS Obelisk_FIND_COMPONENTS)
    if(NOT _obelisk_requested_component STREQUAL "SDK")
        set(Obelisk_${_obelisk_requested_component}_FOUND FALSE)
        set(Obelisk_FOUND FALSE)
        set(Obelisk_NOT_FOUND_MESSAGE
            "Unsupported Obelisk component '${_obelisk_requested_component}'; only SDK is installed.")
        return()
    endif()
endforeach()
unset(_obelisk_requested_component)

set(Obelisk_SDK_BLOCKER_PROMOTION_COUNT 0)
set(Obelisk_SDK_BLOCKER_PROMOTION_TOTAL 12)
set(Obelisk_P0_DEPENDENCY_COUNT 0)
set(Obelisk_P0_DEPENDENCY_TOTAL 4)
set(Obelisk_ACTIVE_COMPLETION_BLOCKER "approved_runtime_evidence_missing")
set(Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE)
set(Obelisk_EXACT_VERSION_REQUESTS_ALLOWED FALSE)
set(Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM FALSE)
set(Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS FALSE)
set(Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE FALSE)
]=])
set(OBELISK_CONFIG_REQUIRED_NON_CLAIM_MARKERS
    [=[set(Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS "package-shape-evidence-only")]=]
    [=[set(Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED FALSE)]=]
    [=[set(Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED FALSE)]=]
    [=[set(Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED FALSE)]=]
    [=[set(Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED FALSE)]=]
    [=[set(Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED FALSE)]=]
    [=[set(Obelisk_V1_COMPLETION_CLAIM_ALLOWED FALSE)]=]
    [=[set(Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED FALSE)]=]
    [=[set(Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED FALSE)]=]
    [=[set(Obelisk_SDK_BLOCKER_PROMOTION_COUNT 0)]=]
    [=[set(Obelisk_SDK_BLOCKER_PROMOTION_TOTAL 12)]=]
    [=[set(Obelisk_P0_DEPENDENCY_COUNT 0)]=]
    [=[set(Obelisk_P0_DEPENDENCY_TOTAL 4)]=]
    [=[set(Obelisk_ACTIVE_COMPLETION_BLOCKER "approved_runtime_evidence_missing")]=]
    [=[set(Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE)]=]
    [=[set(Obelisk_EXACT_VERSION_REQUESTS_ALLOWED FALSE)]=]
    [=[set(Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM FALSE)]=]
    [=[set(Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS FALSE)]=]
    [=[set(Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE FALSE)]=]
)
set(OBELISK_CONFIG_TARGETS_INCLUDE_LINE [=[include("${CMAKE_CURRENT_LIST_DIR}/ObeliskTargets.cmake")]=])
file(READ ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfig.cmake OBELISK_CONFIG_CONTENT)
string(FIND
    "${OBELISK_CONFIG_CONTENT}"
    "${OBELISK_CONFIG_TARGETS_INCLUDE_LINE}"
    OBELISK_CONFIG_TARGETS_INCLUDE_INDEX
)
if(OBELISK_CONFIG_TARGETS_INCLUDE_INDEX EQUAL -1)
    message(FATAL_ERROR "ObeliskConfig.cmake target include marker was not found")
endif()
string(REPLACE
    "${OBELISK_CONFIG_TARGETS_INCLUDE_LINE}"
    "${OBELISK_CONFIG_GUARDRAILS_CONTENT}\ninclude(\"\${CMAKE_CURRENT_LIST_DIR}/ObeliskTargets.cmake\")"
    OBELISK_CONFIG_CONTENT
    "${OBELISK_CONFIG_CONTENT}"
)
foreach(obelisk_config_required_non_claim_marker IN LISTS OBELISK_CONFIG_REQUIRED_NON_CLAIM_MARKERS)
    string(FIND
        "${OBELISK_CONFIG_CONTENT}"
        "${obelisk_config_required_non_claim_marker}"
        OBELISK_CONFIG_REQUIRED_NON_CLAIM_MARKER_INDEX
    )
    if(OBELISK_CONFIG_REQUIRED_NON_CLAIM_MARKER_INDEX EQUAL -1)
        message(FATAL_ERROR
            "Generated ObeliskConfig.cmake missed package-shape non-claim marker: "
            "${obelisk_config_required_non_claim_marker}")
    endif()
endforeach()
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfig.cmake "${OBELISK_CONFIG_CONTENT}")

set(OBELISK_CONFIG_VERSION_CONTENT [=[
set(PACKAGE_VERSION "@PROJECT_VERSION@")
set(PACKAGE_VERSION_COMPATIBLE FALSE)
set(PACKAGE_VERSION_EXACT FALSE)
set(PACKAGE_VERSION_UNSUITABLE FALSE)

if(NOT PACKAGE_FIND_VERSION)
    set(PACKAGE_VERSION_UNSUITABLE TRUE)
    return()
endif()

if(PACKAGE_FIND_VERSION_EXACT)
    set(PACKAGE_VERSION_UNSUITABLE TRUE)
    return()
endif()

if(PACKAGE_FIND_VERSION_MAJOR EQUAL @PROJECT_VERSION_MAJOR@ AND
       PACKAGE_FIND_VERSION_MINOR EQUAL @PROJECT_VERSION_MINOR@ AND
       NOT PACKAGE_FIND_VERSION VERSION_GREATER PACKAGE_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
endif()
]=])
string(CONFIGURE "${OBELISK_CONFIG_VERSION_CONTENT}" OBELISK_CONFIG_VERSION_CONTENT @ONLY)
file(WRITE
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfigVersion.cmake
    "${OBELISK_CONFIG_VERSION_CONTENT}"
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Obelisk
    COMPONENT SDK
)
