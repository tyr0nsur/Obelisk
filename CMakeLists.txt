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

# Create the Obelisk shared library
add_library(obelisk SHARED
    loader/Bootstrap.cpp
    runtime/Logger.cpp
)

# Includes and linking
target_include_directories(obelisk PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(obelisk PRIVATE fmt::fmt spdlog::spdlog dl pthread)

# Ensure visibility is hidden by default, and we only export what we want
# (Good practice for LD_PRELOAD plugins)
set_target_properties(obelisk PROPERTIES CXX_VISIBILITY_PRESET hidden)
set_target_properties(obelisk PROPERTIES VISIBILITY_INLINES_HIDDEN 1)
