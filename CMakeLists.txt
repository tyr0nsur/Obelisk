cmake_minimum_required(VERSION 3.22)
project(Obelisk VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use fPIC as it's a shared library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

enable_testing()
set(SUBHOOK_NO_TESTS ON CACHE BOOL "Disable subhook tests" FORCE)

add_library(obelisk_sdk INTERFACE)
target_include_directories(obelisk_sdk INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# Dependencies
include(FetchContent)

# fmt library
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.1.1
)
FetchContent_MakeAvailable(fmt)

# spdlog library
FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        v1.12.0
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
    ue/Memory.cpp
    ue/ReflectionScanner.cpp
    hooks/HookManager.cpp
    hooks/ProcessEventHook.cpp
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

add_executable(plugin_manager_tests
    tests/core/PluginManagerTests.cpp
    core/EventManager.cpp
    core/PluginConfig.cpp
    core/PluginManager.cpp
    runtime/Logger.cpp
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
