cmake_minimum_required(VERSION 3.22)
project(Obelisk VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

set(OBELISK_DEVELOPMENT_LINE "0.1.0-dev")
set(OBELISK_RELEASE_CHANNEL "dev")
set(OBELISK_API_ABI_VERSION 1)
set(OBELISK_PLUGIN_METADATA_ABI_VERSION 1)
set(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION 1)

# Use fPIC as it's a shared library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

enable_testing()
set(SUBHOOK_NO_TESTS ON CACHE BOOL "Disable subhook tests" FORCE)

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
    ue/InventoryReflection.cpp
    ue/StructureReflection.cpp
    ue/RuntimeReflection.cpp
    ue/ReflectionScanner.cpp
    hooks/HookManager.cpp
    hooks/ProcessEventCallGuard.cpp
    hooks/ProcessEventChatReflection.cpp
    hooks/ProcessEventInventoryReflection.cpp
    hooks/ProcessEventStructureReflection.cpp
    hooks/ProcessEventHook.cpp
    core/ChatEventDispatcher.cpp
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
)
target_include_directories(event_manager_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(event_manager_tests PRIVATE obelisk_sdk fmt::fmt spdlog::spdlog)

add_test(NAME EventManagerTests COMMAND event_manager_tests)

add_executable(chat_event_dispatcher_tests
    tests/core/ChatEventDispatcherTests.cpp
    core/ChatEventDispatcher.cpp
    runtime/Logger.cpp
)
target_include_directories(chat_event_dispatcher_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(chat_event_dispatcher_tests PRIVATE fmt::fmt spdlog::spdlog)

add_test(NAME ChatEventDispatcherTests COMMAND chat_event_dispatcher_tests)

add_executable(plugin_manager_tests
    tests/core/PluginManagerTests.cpp
    core/ChatEventDispatcher.cpp
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

add_executable(abi_layout_tests
    tests/abi/AbiLayoutTests.cpp
)
target_link_libraries(abi_layout_tests PRIVATE obelisk_sdk)

add_test(NAME AbiLayoutTests COMMAND abi_layout_tests)

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
    ue/InventoryReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_inventory_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventInventoryReflectionTests COMMAND process_event_inventory_reflection_tests)

add_executable(process_event_structure_reflection_tests
    tests/core/ProcessEventStructureReflectionTests.cpp
    hooks/ProcessEventStructureReflection.cpp
    ue/StructureReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(process_event_structure_reflection_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_test(NAME ProcessEventStructureReflectionTests COMMAND process_event_structure_reflection_tests)

add_executable(chat_reflection_benchmark EXCLUDE_FROM_ALL
    tests/perf/ChatReflectionBenchmark.cpp
    hooks/ProcessEventChatReflection.cpp
    ue/ChatReflection.cpp
    ue/RuntimeReflection.cpp
)
target_include_directories(chat_reflection_benchmark PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

install(TARGETS obelisk
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    COMPONENT Runtime
)

install(TARGETS obelisk_sdk
    EXPORT ObeliskTargets
    COMPONENT SDK
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
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
