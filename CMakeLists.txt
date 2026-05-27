cmake_minimum_required(VERSION 3.22)
project(Obelisk VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use fPIC as it's a shared library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

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
    core/PluginManager.cpp
)

# Includes and linking
target_include_directories(obelisk PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(obelisk PRIVATE fmt::fmt spdlog::spdlog subhook dl pthread stdc++fs)

# Ensure visibility is hidden by default, and we only export what we want
# (Good practice for LD_PRELOAD plugins)
set_target_properties(obelisk PROPERTIES CXX_VISIBILITY_PRESET hidden)
set_target_properties(obelisk PROPERTIES VISIBILITY_INLINES_HIDDEN 1)
set_target_properties(obelisk PROPERTIES BUILD_RPATH "\$ORIGIN")
set_target_properties(obelisk PROPERTIES INSTALL_RPATH "\$ORIGIN")

add_subdirectory(helloworld_plugin)

option(OBELISK_BUILD_EXPERIMENTAL_CHAT_PLUGIN "Build experimental ChatPlugin" OFF)
if(OBELISK_BUILD_EXPERIMENTAL_CHAT_PLUGIN)
    add_subdirectory(plugins/chat)
endif()
