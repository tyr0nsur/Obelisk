cmake_minimum_required(VERSION 3.22)
project(Obelisk VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

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
    ue/Memory.cpp
    ue/BuffReflection.cpp
    ue/ChatReflection.cpp
    ue/DinoReflection.cpp
    ue/ItemReflection.cpp
    ue/InventoryReflection.cpp
    ue/StructureReflection.cpp
    ue/RuntimeReflection.cpp
    ue/ReflectionScanner.cpp
    hooks/HookManager.cpp
    hooks/ProcessEventCallGuard.cpp
    hooks/ProcessEventDispatch.cpp
    hooks/ProcessEventChatReflection.cpp
    hooks/ProcessEventInventoryReflection.cpp
    hooks/ProcessEventItemReflection.cpp
    hooks/ProcessEventStructureReflection.cpp
    hooks/ProcessEventHook.cpp
    core/ChatEventDispatcher.cpp
    core/InventoryPolicyEventDispatcher.cpp
    core/ItemReturnEventDispatcher.cpp
    core/StructureEventDispatcher.cpp
    core/TimerManager.cpp
    core/EventManager.cpp
    core/PluginConfig.cpp
    core/PluginManager.cpp
)

# Includes and linking
target_include_directories(obelisk PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(obelisk PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog subhook dl pthread stdc++fs)

# Ensure visibility is hidden by default, and we only export what we want
# (Good practice for LD_PRELOAD plugins)
set_target_properties(obelisk PROPERTIES CXX_VISIBILITY_PRESET hidden)
set_target_properties(obelisk PROPERTIES VISIBILITY_INLINES_HIDDEN 1)
set_target_properties(obelisk PROPERTIES BUILD_RPATH "\$ORIGIN")
set_target_properties(obelisk PROPERTIES INSTALL_RPATH "\$ORIGIN")

add_subdirectory(plugins/oBaseEvents)
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

add_executable(plugin_manager_tests
    tests/core/PluginManagerTests.cpp
    core/ChatEventDispatcher.cpp
    core/InventoryPolicyEventDispatcher.cpp
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
target_link_libraries(plugin_manager_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog dl stdc++fs)

add_test(NAME PluginManagerTests COMMAND plugin_manager_tests)

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

install(FILES include/obelisk/ObeliskApi.h
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

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMinorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/ObeliskConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Obelisk
    COMPONENT SDK
)
